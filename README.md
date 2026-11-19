# Chess Engine + Szachy online

A chess engine written from scratch in Python (following the [Chess Programming Wiki](https://www.chessprogramming.org/)), and a website built on top of it where two people play chess against each other in the browser.

The engine is the rules authority of the website: every move a player makes is validated by the bitboard move generator on the server, which also detects checkmate, stalemate and every draw rule.

## Features

**Engine**
- Bitboard board representation, precomputed king/knight/pawn tables, magic bitboards for sliding pieces
- Full legal move generation incl. castling, en passant and promotion, validated with perft against the CPW reference positions
- FEN import/export, UCI move parsing, SAN notation (with disambiguation, check and mate marks), PGN export
- Game end detection: checkmate, stalemate, threefold repetition, fifty-move rule, insufficient material

**Website**
- Accounts (register / log in), passwords hashed with scrypt, cookie sessions
- Lobby: create a game with a time control (1+0 up to 60+30) and colour, share the link or join open games
- Live games over WebSockets, server-side clocks with increment, flag detection (incl. the "timeout vs insufficient material" draw)
- Drag-and-drop or click-click moves, legal move highlighting, promotion picker, last move and check highlighting
- Resign, draw offer / accept / decline, abort before the first moves, automatic abort if White never moves
- Move list with position browsing (arrow keys), spectator mode, game history with results and PGN download
- Responsive layout (phone and desktop), custom SVG pieces

## Project layout

| Path | What it is |
|---|---|
| `chess_engine.py` | `Bitboard` class: board state, move generation, make/unmake, check detection, FEN loading |
| `helpers.py` | Bitboard utilities and precomputed move tables |
| `move.py` | `Move` object |
| `game.py` | A whole game on top of the engine: UCI parsing, SAN, FEN export, game end rules, PGN |
| `perft.py` | Perft node counter used to validate move generation |
| `server/app.py` | FastAPI app: pages, JSON API (accounts, lobby, history, PGN) and the game WebSocket |
| `server/live.py` | Live game logic: clocks, moves, resign/draw/abort, broadcasting state to players |
| `server/auth.py` | Password hashing and sessions |
| `server/db.py` | MongoDB connection and indexes |
| `server/static/` | Frontend (plain HTML/CSS/JS modules, no build step) |
| `generate_magics/` | C++ tool that generates `magic_numbers.json` |
| `tests/` | Engine, perft, game rules and end-to-end server tests |

## Running locally

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt     # on Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m uvicorn server.app:app --reload
```

Open http://localhost:8000. Without `MONGODB_URI` the server uses an in-memory database (data disappears on restart), so nothing else needs to be installed. To test two players on one computer, open the second player in a private window or at http://127.0.0.1:8000 (cookies are per host).

Run the tests:

```bash
.venv/Scripts/python -m pytest
```

## Configuration

| Variable | Meaning |
|---|---|
| `MONGODB_URI` | MongoDB connection string. Unset = in-memory database for development |
| `MONGODB_DB` | Database name (default `szachy`) |
| `COOKIE_SECURE` | `1` in production (HTTPS) so the session cookie is only sent over HTTPS |

## Deployment (free)

The app needs a long-running process for WebSockets, so serverless hosts such as Vercel don't fit. The free setup:

1. **Database: MongoDB Atlas.** Create a free M0 cluster at https://www.mongodb.com/cloud/atlas, add a database user, allow access from anywhere (`0.0.0.0/0`, Render has no fixed IP on the free plan) and copy the connection string (`mongodb+srv://...`).
2. **App: Render.** Push this repository to GitHub, then in Render choose *New → Blueprint* and pick the repository. `render.yaml` sets everything up; paste the Atlas connection string as `MONGODB_URI` when asked.
3. Open the `https://<name>.onrender.com` address Render gives you.

Notes:
- Free Render services sleep after ~15 minutes without traffic; the first visit afterwards takes about 30–60 seconds.
- Live games are held in memory, so keep exactly one instance. Game state is also saved to MongoDB after every move, so a restart only interrupts the connection: players reconnect automatically and the game continues.

## Roadmap

Engine search (negamax with alpha-beta) and evaluation are the next engine stages; once they exist, the website can get a "play against the computer" mode.
