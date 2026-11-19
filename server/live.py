"""Live games: the rules of a match (clocks, resign, draws, aborts) and pushing state to
browsers over WebSockets.

The server is the only authority. A browser sends "I want to play e2e4"; the server checks
it with the engine, updates the clocks, saves the game and broadcasts the new state to
both players (and any spectators).
"""
import asyncio
import json
import logging
import secrets
from datetime import timedelta

from game import Game, IllegalMove, WHITE_WINS, BLACK_WINS, DRAW, square_name

from .db import aware, get_db, utcnow

log = logging.getLogger("chess.live")

FIRST_MOVE_SECONDS = 60  # white must make the first move within this time or the game is aborted


class GameError(Exception):
    """A request that breaks the rules of the match (shown to the user)."""


def color_of(doc, user_id):
    if user_id is not None and doc.get("white_id") == user_id:
        return "white"
    if user_id is not None and doc.get("black_id") == user_id:
        return "black"
    return None


def other(color):
    return "black" if color == "white" else "white"


def win_for(color):
    return WHITE_WINS if color == "white" else BLACK_WINS


class LiveGame:
    def __init__(self, doc):
        self.id = doc["_id"]
        self.doc = doc  # the game document, saved back to MongoDB after every change
        self.lock = asyncio.Lock()
        self.connections = {}  # websocket -> user_id
        self.timer = None
        self.game = Game.from_uci_moves(doc["moves"])

    def save(self):
        get_db().games.replace_one({"_id": self.id}, self.doc)

    # ---------- clocks ----------

    def side_to_move(self):
        return "white" if self.game.white_to_move else "black"

    def live_clocks(self, now=None):
        """Remaining time of both players right now (the running clock is ticking)."""
        doc = self.doc
        clocks = {"white": doc["white_ms"], "black": doc["black_ms"]}
        if doc["status"] == "active" and doc.get("turn_started_at") is not None:
            elapsed = int(((now or utcnow()) - aware(doc["turn_started_at"])).total_seconds() * 1000)
            side = self.side_to_move()
            clocks[side] = max(0, clocks[side] - elapsed)
        return clocks

    def first_move_deadline(self):
        doc = self.doc
        if doc["status"] == "active" and not doc["moves"] and doc.get("started_at") is not None:
            return aware(doc["started_at"]) + timedelta(seconds=FIRST_MOVE_SECONDS)
        return None

    # ---------- state changes (call with self.lock held) ----------

    def _finish(self, result, termination, now):
        clocks = self.live_clocks(now)
        self.doc.update(white_ms=clocks["white"], black_ms=clocks["black"], status="finished",
                        result=result, termination=termination, turn_started_at=None,
                        draw_offer=None, finished_at=now)
        self.save()

    def _abort(self, now):
        self.doc.update(status="aborted", turn_started_at=None, draw_offer=None, finished_at=now)
        self.save()

    def check_time(self, now=None):
        """Flag a player whose clock ran out, or abort a game nobody started.
        Returns True when the game state changed."""
        now = now or utcnow()
        doc = self.doc
        if doc["status"] != "active":
            return False
        deadline = self.first_move_deadline()
        if deadline is not None and now >= deadline:
            self._abort(now)
            return True
        if doc.get("turn_started_at") is None:
            return False
        side = self.side_to_move()
        if self.live_clocks(now)[side] > 0:
            return False
        # Running out of time loses, unless the opponent could never checkmate (FIDE 6.9)
        if self.game.can_mate(side == "black"):
            self._finish(win_for(other(side)), "timeout", now)
        else:
            self._finish(DRAW, "timeout_vs_insufficient", now)
        return True

    def join(self, user):
        doc = self.doc
        if doc["status"] != "waiting":
            raise GameError("Ta partia już się rozpoczęła.")
        if doc["creator_id"] == user["id"]:
            raise GameError("Nie możesz grać sam ze sobą.")
        creator_color = doc["creator_color"]
        if creator_color == "random":
            creator_color = secrets.choice(["white", "black"])
        creator = (doc["creator_id"], doc["creator"])
        joiner = (user["id"], user["username"])
        white, black = (creator, joiner) if creator_color == "white" else (joiner, creator)
        doc.update(white_id=white[0], white=white[1], black_id=black[0], black=black[1],
                   status="active", started_at=utcnow(),
                   white_ms=doc["initial_ms"], black_ms=doc["initial_ms"])
        self.save()

    def move(self, user_id, uci):
        now = utcnow()
        doc = self.doc
        if self.check_time(now):
            return
        if doc["status"] != "active":
            raise GameError("Partia nie trwa.")
        color = color_of(doc, user_id)
        if color is None:
            raise GameError("Nie grasz w tej partii.")
        if color != self.side_to_move():
            raise GameError("Teraz ruch przeciwnika.")
        try:
            self.game.push_uci(uci)
        except IllegalMove:
            raise GameError("Niedozwolony ruch.")

        if doc.get("turn_started_at") is not None:
            # The side to move has already switched, so compute the mover's time directly
            elapsed = int((now - aware(doc["turn_started_at"])).total_seconds() * 1000)
            key = color + "_ms"
            doc[key] = max(0, doc[key] - elapsed) + doc["increment_ms"]
        doc["turn_started_at"] = now
        doc["moves"] = list(self.game.uci_moves)
        # Moving declines a draw offered by the opponent
        if doc.get("draw_offer") == other(color):
            doc["draw_offer"] = None

        outcome = self.game.outcome()
        if outcome:
            self._finish(outcome[0], outcome[1], now)
        else:
            self.save()

    def resign(self, user_id):
        color = self._player_in_active_game(user_id)
        self._finish(win_for(other(color)), "resign", utcnow())

    def offer_draw(self, user_id):
        color = self._player_in_active_game(user_id)
        offer = self.doc.get("draw_offer")
        if offer == other(color):
            self._finish(DRAW, "agreement", utcnow())
        elif offer is None:
            self.doc["draw_offer"] = color
            self.save()

    def accept_draw(self, user_id):
        color = self._player_in_active_game(user_id)
        if self.doc.get("draw_offer") != other(color):
            raise GameError("Przeciwnik nie proponuje remisu.")
        self._finish(DRAW, "agreement", utcnow())

    def decline_draw(self, user_id):
        color = self._player_in_active_game(user_id)
        if self.doc.get("draw_offer") == other(color):
            self.doc["draw_offer"] = None
            self.save()

    def abort(self, user_id):
        doc = self.doc
        if doc["status"] == "waiting":
            if doc["creator_id"] != user_id:
                raise GameError("Tylko twórca może anulować partię.")
            self._abort(utcnow())
            return
        self._player_in_active_game(user_id)
        if len(doc["moves"]) >= 2:
            raise GameError("Partię można przerwać tylko przed pierwszymi ruchami.")
        self._abort(utcnow())

    def _player_in_active_game(self, user_id):
        if self.check_time():
            raise GameError("Partia już się zakończyła.")
        if self.doc["status"] != "active":
            raise GameError("Partia nie trwa.")
        color = color_of(self.doc, user_id)
        if color is None:
            raise GameError("Nie grasz w tej partii.")
        return color

    # ---------- what the browser sees ----------

    def state_for(self, user_id):
        doc = self.doc
        game = self.game
        you = color_of(doc, user_id)
        turn = self.side_to_move()
        active = doc["status"] == "active"
        check_square = None
        if game.moves and game.is_check():
            check_square = square_name(game.king_square(game.white_to_move))
        deadline = self.first_move_deadline()
        return {
            "type": "state",
            "id": self.id,
            "status": doc["status"],
            "result": doc.get("result"),
            "termination": doc.get("termination"),
            "white": doc.get("white"),
            "black": doc.get("black"),
            "creator": doc["creator"],
            "creatorColor": doc["creator_color"],
            "you": you,
            "isCreator": user_id is not None and doc["creator_id"] == user_id,
            "initialMs": doc["initial_ms"],
            "incrementMs": doc["increment_ms"],
            "moves": game.uci_moves,
            "san": game.san_moves,
            "fens": game.fens,
            "turn": turn,
            "legal": game.legal_uci_moves() if active and you == turn else [],
            "lastMove": game.uci_moves[-1] if game.uci_moves else None,
            "check": check_square,
            "clocks": self.live_clocks(),
            "clockRunning": turn if active and doc.get("turn_started_at") is not None else None,
            "drawOffer": doc.get("draw_offer"),
            "abortInMs": max(0, int((deadline - utcnow()).total_seconds() * 1000)) if deadline else None,
        }

    async def send_state(self, ws, user_id):
        await ws.send_text(json.dumps(self.state_for(user_id)))

    async def broadcast(self):
        for ws, user_id in list(self.connections.items()):
            try:
                await self.send_state(ws, user_id)
            except Exception:
                self.connections.pop(ws, None)


class GameManager:
    """Keeps games that are being played or watched in memory, one LiveGame per id."""

    def __init__(self):
        self.games = {}

    def get(self, game_id):
        live = self.games.get(game_id)
        if live is None:
            doc = get_db().games.find_one({"_id": game_id})
            if doc is None:
                return None
            live = LiveGame(doc)
            self.games[game_id] = live
            self.schedule(live)
        return live

    def forget_if_idle(self, live):
        if not live.connections and live.doc["status"] not in ("active", "waiting"):
            if live.timer:
                live.timer.cancel()
            self.games.pop(live.id, None)

    def schedule(self, live):
        """(Re)arm the timer that flags a player when their clock hits zero."""
        if live.timer:
            live.timer.cancel()
            live.timer = None
        doc = live.doc
        if doc["status"] != "active":
            return
        deadline = live.first_move_deadline()
        if deadline is not None:
            delay = (deadline - utcnow()).total_seconds()
        elif doc.get("turn_started_at") is not None:
            delay = live.live_clocks()[live.side_to_move()] / 1000
        else:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # no event loop (plain synchronous code)
        live.timer = loop.create_task(self._timeout(live, max(0.0, delay) + 0.05))

    async def _timeout(self, live, delay):
        await asyncio.sleep(delay)
        async with live.lock:
            changed = live.check_time()
        if changed:
            live.timer = None
            await live.broadcast()
            self.forget_if_idle(live)
        else:
            self.schedule(live)

    async def act(self, live, action, user, payload=None):
        """Run a player's action under the game's lock, then notify everyone.
        `user` is {"id", "username"}."""
        user_id = user["id"]
        async with live.lock:
            try:
                if action == "join":
                    live.join(user)
                elif action == "move":
                    live.move(user_id, (payload or {}).get("uci"))
                elif action == "resign":
                    live.resign(user_id)
                elif action == "offer_draw":
                    live.offer_draw(user_id)
                elif action == "accept_draw":
                    live.accept_draw(user_id)
                elif action == "decline_draw":
                    live.decline_draw(user_id)
                elif action == "abort":
                    live.abort(user_id)
                else:
                    raise GameError("Nieznana akcja.")
            except GameError:
                raise
            except Exception:
                log.exception("action %s failed", action)
                # drop the cached copy so the next access reloads the true state
                self.games.pop(live.id, None)
                raise GameError("Błąd serwera.")
        self.schedule(live)
        await live.broadcast()
        self.forget_if_idle(live)

    def resume_active_games(self):
        """After a restart, re-arm clocks of games that were in progress."""
        for doc in get_db().games.find({"status": "active"}, {"_id": 1}):
            self.get(doc["_id"])
