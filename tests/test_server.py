"""End-to-end tests of the web server: accounts, lobby, and full games over WebSockets.

Runs against the in-memory MongoDB (mongomock), so no database server is needed.
"""
import os
from datetime import timedelta

import pytest

os.environ.pop("MONGODB_URI", None)

from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from server import app as app_module  # noqa: E402
from server import db as db_module  # noqa: E402

_counter = 0


class Player:
    """One logged-in user. All players share a single TestClient (one event loop, like the
    real server) and send their own session cookie with every request."""

    def __init__(self, client, name=None, password="sekret123", register=True):
        global _counter
        _counter += 1
        self.client = client
        self.name = name or f"user{_counter}"
        self.token = None
        if register:
            r = self.post("/api/register", json={"username": self.name, "password": password})
            assert r.status_code == 200, r.text
            self.token = r.cookies.get("session")

    def _headers(self):
        return {"cookie": f"session={self.token}"} if self.token else {}

    def request(self, method, url, **kwargs):
        self.client.cookies.clear()
        r = self.client.request(method, url, headers=self._headers(), **kwargs)
        self.client.cookies.clear()
        return r

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def ws(self, game_id):
        self.client.cookies.clear()
        return self.client.websocket_connect(f"/ws/game/{game_id}", headers=self._headers())


@pytest.fixture(scope="module")
def server():
    db_module.reset_for_tests()
    with TestClient(app_module.app) as client:
        yield client


def new_user(server):
    return Player(server)


def start_game(server, minutes=5, increment=0, color="white"):
    a, b = Player(server), Player(server)
    game_id = a.post("/api/games", json={"minutes": minutes, "increment": increment, "color": color}).json()["id"]
    assert b.post(f"/api/games/{game_id}/join").status_code == 200, "join failed"
    return a, b, game_id


def recv_state(ws):
    while True:
        msg = ws.receive_json()
        if msg["type"] == "state":
            return msg


def test_register_login_logout(server):
    user = new_user(server)
    assert user.get("/api/me").json() == {"username": user.name, "guest": False}
    user.post("/api/logout")
    assert user.get("/api/me").status_code == 401

    other = Player(server, register=False)
    assert other.post("/api/login", json={"username": user.name.upper(), "password": "zle-haslo"}).status_code == 401
    r = other.post("/api/login", json={"username": user.name.upper(), "password": "sekret123"})
    assert r.status_code == 200
    other.token = r.cookies.get("session")
    assert other.get("/api/me").json()["username"] == user.name


def test_register_validation(server):
    client = Player(server, register=False)
    assert client.post("/api/register", json={"username": "ab", "password": "sekret123"}).status_code == 400
    assert client.post("/api/register", json={"username": "ok_name", "password": "123"}).status_code == 400
    assert client.post("/api/register", json={"username": "dup", "password": "sekret123"}).status_code == 200
    assert client.post("/api/register", json={"username": "DUP", "password": "sekret123"}).status_code == 409


def test_api_requires_login(server):
    anon = Player(server, register=False)
    assert anon.get("/api/games/open").status_code == 401
    assert anon.post("/api/games", json={"minutes": 5, "increment": 0}).status_code == 401


def test_pages_served(server):
    for path in ["/", "/login", "/history", "/game/abc"]:
        r = server.get(path)
        assert r.status_code == 200 and "<html" in r.text.lower()


def test_lobby_create_join_cancel(server):
    a, b = new_user(server), new_user(server)
    gid = a.post("/api/games", json={"minutes": 3, "increment": 2, "color": "black"}).json()["id"]
    assert any(g["id"] == gid and g["mine"] for g in a.get("/api/games/open").json())
    assert a.post(f"/api/games/{gid}/join").status_code == 400  # can't play yourself

    gid2 = a.post("/api/games", json={"minutes": 3, "increment": 2}).json()["id"]
    assert b.post(f"/api/games/{gid2}/cancel").status_code == 400  # not the creator
    assert a.post(f"/api/games/{gid2}/cancel").status_code == 200
    assert all(g["id"] != gid2 for g in a.get("/api/games/open").json())

    assert b.post(f"/api/games/{gid}/join").status_code == 200
    assert b.post(f"/api/games/{gid}/join").status_code == 400  # already started
    active = b.get("/api/my-games").json()["active"]
    assert active[0]["id"] == gid and active[0]["you"] == "white"  # creator asked for black


def test_waiting_game_limit(server):
    a = new_user(server)
    for _ in range(3):
        assert a.post("/api/games", json={"minutes": 5, "increment": 0}).status_code == 200
    assert a.post("/api/games", json={"minutes": 5, "increment": 0}).status_code == 400


def test_full_game_checkmate_over_websocket(server):
    white, black, gid = start_game(server)
    with white.ws(gid) as ws_w, black.ws(gid) as ws_b:
        s = recv_state(ws_w)
        assert s["you"] == "white" and s["status"] == "active" and len(s["legal"]) == 20
        assert recv_state(ws_b)["legal"] == []  # not black's turn

        # black may not move first
        ws_b.send_json({"type": "move", "uci": "e7e5"})
        assert ws_b.receive_json()["type"] == "error"
        recv_state(ws_b)

        for i, uci in enumerate(["f2f3", "e7e5", "g2g4", "d8h4"]):
            (ws_w if i % 2 == 0 else ws_b).send_json({"type": "move", "uci": uci})
            sw, sb = recv_state(ws_w), recv_state(ws_b)
            assert sw["moves"] == sb["moves"]
        assert sw["status"] == "finished"
        assert sw["result"] == "0-1" and sw["termination"] == "checkmate"
        assert sw["san"] == ["f3", "e5", "g4", "Qh4#"]
        assert sw["check"] == "e1"

    hist = white.get("/api/my-games").json()["finished"]
    assert hist[0]["id"] == gid and hist[0]["result"] == "0-1"
    pgn = white.get(f"/api/games/{gid}/pgn").text
    assert "1. f3 e5 2. g4 Qh4# 0-1" in pgn


def test_illegal_move_rejected(server):
    white, _, gid = start_game(server)
    with white.ws(gid) as ws:
        recv_state(ws)
        ws.send_json({"type": "move", "uci": "e2e5"})
        assert ws.receive_json() == {"type": "error", "message": "Niedozwolony ruch."}
        assert recv_state(ws)["moves"] == []


def test_resign(server):
    white, black, gid = start_game(server)
    with black.ws(gid) as ws:
        recv_state(ws)
        ws.send_json({"type": "resign"})
        s = recv_state(ws)
        assert (s["status"], s["result"], s["termination"]) == ("finished", "1-0", "resign")


def test_draw_offer_accept_and_decline(server):
    white, black, gid = start_game(server)
    with white.ws(gid) as ws_w, black.ws(gid) as ws_b:
        recv_state(ws_w), recv_state(ws_b)
        ws_w.send_json({"type": "offer_draw"})
        assert recv_state(ws_w)["drawOffer"] == "white"
        assert recv_state(ws_b)["drawOffer"] == "white"

        ws_b.send_json({"type": "decline_draw"})
        assert recv_state(ws_w)["drawOffer"] is None
        recv_state(ws_b)

        ws_w.send_json({"type": "offer_draw"})
        recv_state(ws_w), recv_state(ws_b)
        ws_b.send_json({"type": "accept_draw"})
        s = recv_state(ws_w)
        recv_state(ws_b)
        assert (s["result"], s["termination"]) == ("1/2-1/2", "agreement")


def test_abort_only_at_start(server):
    white, black, gid = start_game(server)
    with white.ws(gid) as ws_w, black.ws(gid) as ws_b:
        recv_state(ws_w), recv_state(ws_b)
        for ws, uci in [(ws_w, "e2e4"), (ws_b, "e7e5")]:
            ws.send_json({"type": "move", "uci": uci})
            recv_state(ws_w), recv_state(ws_b)
        ws_w.send_json({"type": "abort"})
        assert ws_w.receive_json()["type"] == "error"

    white, black, gid = start_game(server)
    with black.ws(gid) as ws:
        recv_state(ws)
        ws.send_json({"type": "abort"})
        assert recv_state(ws)["status"] == "aborted"


def test_spectator_cannot_move(server):
    _, _, gid = start_game(server)
    viewer = new_user(server)
    with viewer.ws(gid) as ws:
        s = recv_state(ws)
        assert s["you"] is None and s["legal"] == []
        ws.send_json({"type": "move", "uci": "e2e4"})
        assert ws.receive_json()["message"] == "Nie grasz w tej partii."


def test_websocket_requires_login(server):
    anon = Player(server, register=False)
    with pytest.raises(WebSocketDisconnect):
        with anon.ws("whatever") as ws:
            ws.receive_json()


def _shift_clock(gid, seconds):
    """Pretend the side to move started thinking `seconds` earlier."""
    live = app_module.manager.games[gid]
    live.doc["turn_started_at"] = live.doc["turn_started_at"] - timedelta(seconds=seconds)


def test_clock_and_increment(server):
    white, black, gid = start_game(server, minutes=1, increment=2)
    with white.ws(gid) as ws_w, black.ws(gid) as ws_b:
        recv_state(ws_w), recv_state(ws_b)
        ws_w.send_json({"type": "move", "uci": "e2e4"})       # first move: clock not running yet
        s = recv_state(ws_w)
        recv_state(ws_b)
        assert s["clocks"]["white"] == 60000 and s["clockRunning"] == "black"

        _shift_clock(gid, 10)
        ws_b.send_json({"type": "move", "uci": "e7e5"})
        s = recv_state(ws_b)
        recv_state(ws_w)
        assert 51500 <= s["clocks"]["black"] <= 52000          # 60 - 10 + 2 increment


def test_timeout_flags_player(server):
    white, black, gid = start_game(server, minutes=1)
    with white.ws(gid) as ws_w, black.ws(gid) as ws_b:
        recv_state(ws_w), recv_state(ws_b)
        ws_w.send_json({"type": "move", "uci": "e2e4"})
        recv_state(ws_w), recv_state(ws_b)
        _shift_clock(gid, 61)
        # black tries to move after the flag fell: the game ends on time instead
        ws_b.send_json({"type": "move", "uci": "e7e5"})
        s = recv_state(ws_b)
        assert (s["status"], s["result"], s["termination"]) == ("finished", "1-0", "timeout")
        assert s["moves"] == ["e2e4"]


def test_first_move_deadline_aborts(server):
    white, _, gid = start_game(server)
    live = app_module.manager.get(gid)
    live.doc["started_at"] = live.doc["started_at"] - timedelta(seconds=61)
    with white.ws(gid) as ws:
        recv_state(ws)
        ws.send_json({"type": "move", "uci": "e2e4"})
        assert recv_state(ws)["status"] == "aborted"


def test_game_survives_restart(server):
    white, black, gid = start_game(server)
    with white.ws(gid) as ws:
        recv_state(ws)
        ws.send_json({"type": "move", "uci": "d2d4"})
        recv_state(ws)
    # drop the in-memory copy: the next connection must rebuild it from the database
    app_module.manager.games.pop(gid, None)
    with black.ws(gid) as ws:
        s = recv_state(ws)
        assert s["moves"] == ["d2d4"] and "d7d5" in s["legal"]
    assert db_module.get_db().games.find_one({"_id": gid})["moves"] == ["d2d4"]


def test_guest_can_join_and_play(server):
    creator = new_user(server)
    gid = creator.post("/api/games", json={"minutes": 5, "increment": 0, "color": "white"}).json()["id"]

    guest = Player(server, register=False)
    assert guest.get("/api/me").status_code == 401
    r = guest.post("/api/guest")
    assert r.status_code == 200 and r.json()["guest"] is True
    guest.token = r.cookies.get("session")
    me = guest.get("/api/me").json()
    assert me["guest"] is True and me["username"].startswith("Gosc-")
    # calling it again keeps the same guest instead of creating a new one
    assert guest.post("/api/guest").json()["username"] == me["username"]

    assert guest.post(f"/api/games/{gid}/join").status_code == 200
    with creator.ws(gid) as ws_w, guest.ws(gid) as ws_b:
        recv_state(ws_w)
        assert recv_state(ws_b)["you"] == "black"
        ws_w.send_json({"type": "move", "uci": "e2e4"})
        recv_state(ws_w), recv_state(ws_b)
        ws_b.send_json({"type": "move", "uci": "e7e5"})
        assert recv_state(ws_b)["moves"] == ["e2e4", "e7e5"]

    # nobody can log into a guest account, and the name prefix is reserved
    anon = Player(server, register=False)
    assert anon.post("/api/login", json={"username": me["username"], "password": ""}).status_code == 401
    assert anon.post("/api/register", json={"username": "Gosc-1", "password": "sekret123"}).status_code == 400
