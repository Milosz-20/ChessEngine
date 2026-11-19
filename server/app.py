"""FastAPI application: pages, JSON API for accounts / lobby / history, and the WebSocket
that carries a live game.

Run locally:  uvicorn server.app:app --reload
"""
import json
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from game import Game, build_pgn

from . import auth
from .db import aware, get_db, init_db, utcnow
from .live import GameError, GameManager

STATIC = Path(__file__).parent / "static"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"
MAX_WAITING_PER_USER = 3

manager = GameManager()


@asynccontextmanager
async def lifespan(app):
    init_db()
    manager.resume_active_games()
    yield


app = FastAPI(title="Szachy", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------- helpers ----------

def current_user(request: Request):
    user = auth.user_from_token(request.cookies.get(auth.SESSION_COOKIE))
    if user is None:
        raise HTTPException(401, "Musisz się zalogować.")
    return user


def set_session_cookie(response: Response, token):
    response.set_cookie(auth.SESSION_COOKIE, token, max_age=auth.SESSION_DAYS * 86400,
                        httponly=True, samesite="lax", secure=COOKIE_SECURE, path="/")


def iso(dt):
    return aware(dt).isoformat() if dt else None


def game_summary(doc, user_id=None):
    you = None
    if user_id is not None:
        you = "white" if doc.get("white_id") == user_id else "black" if doc.get("black_id") == user_id else None
    return {
        "id": doc["_id"],
        "white": doc.get("white"),
        "black": doc.get("black"),
        "creator": doc["creator"],
        "creatorColor": doc["creator_color"],
        "minutes": doc["initial_ms"] / 60000,
        "increment": doc["increment_ms"] // 1000,
        "status": doc["status"],
        "result": doc.get("result"),
        "termination": doc.get("termination"),
        "moves": len(doc["moves"]),
        "you": you,
        "mine": user_id is not None and doc["creator_id"] == user_id,
        "createdAt": iso(doc.get("created_at")),
        "finishedAt": iso(doc.get("finished_at")),
    }


# ---------- pages ----------

def page(name):
    return FileResponse(STATIC / name, headers={"Cache-Control": "no-cache"})


@app.get("/", include_in_schema=False)
def index_page():
    return page("index.html")


@app.get("/login", include_in_schema=False)
def login_page():
    return page("login.html")


@app.get("/history", include_in_schema=False)
def history_page():
    return page("history.html")


@app.get("/game/{game_id}", include_in_schema=False)
def game_page(game_id: str):
    return page("game.html")


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True}


# ---------- accounts ----------

class Credentials(BaseModel):
    username: str
    password: str


@app.post("/api/register")
def register(body: Credentials, response: Response):
    username = body.username.strip()
    error = auth.validate_new_account(username, body.password)
    if error:
        raise HTTPException(400, error)
    try:
        user = auth.create_user(username, body.password)
    except auth.UsernameTaken:
        raise HTTPException(409, "Ta nazwa użytkownika jest zajęta.")
    set_session_cookie(response, auth.create_session(user))
    return {"username": user["username"]}


@app.post("/api/login")
def login(body: Credentials, response: Response):
    user = auth.find_user(body.username.strip())
    if user is None or not auth.verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Nieprawidłowa nazwa użytkownika lub hasło.")
    set_session_cookie(response, auth.create_session(user))
    return {"username": user["username"]}


@app.post("/api/guest")
def guest(request: Request, response: Response):
    """Play without an account: create a guest user and log the browser into it."""
    user = auth.user_from_token(request.cookies.get(auth.SESSION_COOKIE))
    if user is not None:
        return {"username": user["username"], "guest": user["guest"]}
    guest_user = auth.create_guest()
    set_session_cookie(response, auth.create_session(guest_user))
    return {"username": guest_user["username"], "guest": True}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    auth.delete_session(request.cookies.get(auth.SESSION_COOKIE))
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {"username": user["username"], "guest": user["guest"]}


# ---------- lobby ----------

class NewGame(BaseModel):
    minutes: float
    increment: int
    color: str = "random"


@app.post("/api/games")
def create_game(body: NewGame, user=Depends(current_user)):
    if body.color not in ("white", "black", "random"):
        raise HTTPException(400, "Nieprawidłowy kolor.")
    if not (0.5 <= body.minutes <= 180) or not (0 <= body.increment <= 60):
        raise HTTPException(400, "Nieprawidłowe tempo gry.")
    games = get_db().games
    if games.count_documents({"creator_id": user["id"], "status": "waiting"}) >= MAX_WAITING_PER_USER:
        raise HTTPException(400, f"Możesz mieć najwyżej {MAX_WAITING_PER_USER} oczekujące partie.")
    initial_ms = int(body.minutes * 60000)
    doc = {
        "_id": secrets.token_urlsafe(6),
        "creator_id": user["id"], "creator": user["username"], "creator_color": body.color,
        "white_id": None, "white": None, "black_id": None, "black": None,
        "initial_ms": initial_ms, "increment_ms": body.increment * 1000,
        "white_ms": initial_ms, "black_ms": initial_ms, "turn_started_at": None,
        "status": "waiting", "moves": [], "result": None, "termination": None, "draw_offer": None,
        "created_at": utcnow(), "started_at": None, "finished_at": None,
    }
    games.insert_one(doc)
    return {"id": doc["_id"]}


@app.get("/api/games/open")
def open_games(user=Depends(current_user)):
    docs = get_db().games.find({"status": "waiting"}).sort("created_at", -1).limit(50)
    return [game_summary(d, user["id"]) for d in docs]


@app.get("/api/my-games")
def my_games(user=Depends(current_user)):
    games = get_db().games
    mine = [{"white_id": user["id"]}, {"black_id": user["id"]}]
    active = games.find({"$or": mine, "status": "active"}).sort("started_at", -1)
    finished = games.find({"$or": mine, "status": "finished"}).sort("finished_at", -1).limit(200)
    return {"active": [game_summary(d, user["id"]) for d in active],
            "finished": [game_summary(d, user["id"]) for d in finished]}


async def run_action(game_id, action, user):
    live = manager.get(game_id)
    if live is None:
        raise HTTPException(404, "Nie ma takiej partii.")
    try:
        await manager.act(live, action, user)
    except GameError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.post("/api/games/{game_id}/join")
async def join_game(game_id: str, user=Depends(current_user)):
    return await run_action(game_id, "join", user)


@app.post("/api/games/{game_id}/cancel")
async def cancel_game(game_id: str, user=Depends(current_user)):
    return await run_action(game_id, "abort", user)


@app.get("/api/games/{game_id}/pgn")
def game_pgn(game_id: str, user=Depends(current_user)):
    doc = get_db().games.find_one({"_id": game_id})
    if doc is None or doc["status"] == "waiting":
        raise HTTPException(404, "Nie ma takiej partii.")
    game = Game.from_uci_moves(doc["moves"])
    result = doc.get("result") or "*"
    started = aware(doc.get("started_at") or doc["created_at"])
    headers = {
        "Event": "Partia towarzyska",
        "Site": "Szachy online",
        "Date": started.strftime("%Y.%m.%d"),
        "White": doc.get("white") or "?",
        "Black": doc.get("black") or "?",
        "Result": result,
        "TimeControl": f"{doc['initial_ms'] // 1000}+{doc['increment_ms'] // 1000}",
        "Termination": doc.get("termination") or "unterminated",
    }
    return PlainTextResponse(build_pgn(headers, game.san_moves, result), headers={
        "Content-Disposition": f'attachment; filename="partia-{game_id}.pgn"'})


# ---------- live game ----------

def origin_allowed(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if not origin:
        return True  # non-browser clients
    return urlparse(origin).netloc == websocket.headers.get("host")


@app.websocket("/ws/game/{game_id}")
async def game_socket(websocket: WebSocket, game_id: str):
    if not origin_allowed(websocket):
        await websocket.close(code=4403)
        return
    user = auth.user_from_token(websocket.cookies.get(auth.SESSION_COOKIE))
    if user is None:
        await websocket.close(code=4401)
        return
    live = manager.get(game_id)
    if live is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    live.connections[websocket] = user["id"]
    try:
        await live.send_state(websocket, user["id"])
        while True:
            try:
                message = json.loads(await websocket.receive_text())
            except ValueError:
                continue
            if not isinstance(message, dict):
                continue
            action = message.get("type")
            if action == "ping":
                await websocket.send_text('{"type":"pong"}')
                continue
            # the in-memory game may have been reloaded after an error
            live = manager.get(game_id) or live
            live.connections[websocket] = user["id"]
            try:
                await manager.act(live, action, user, message)
            except GameError as e:
                await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
                # resend the true state so a rejected move snaps back
                await live.send_state(websocket, user["id"])
    except WebSocketDisconnect:
        pass
    finally:
        live.connections.pop(websocket, None)
        manager.forget_if_idle(live)
