"""MongoDB storage.

Production: set MONGODB_URI (e.g. a free MongoDB Atlas cluster).
Local development without MongoDB installed: leave it unset and an in-memory database
(mongomock) is used instead; it is wiped when the server stops.

Collections
  users     {_id: ObjectId, username, username_lower, password_hash, created_at}
  sessions  {_id: sha256(token), user_id, expires_at}
  games     {_id: short id, creator_id, white_id, black_id, creator, white, black,
             creator_color, initial_ms, increment_ms, white_ms, black_ms, turn_started_at,
             status, moves: [uci...], result, termination, draw_offer,
             created_at, started_at, finished_at}
  Usernames never change, so games store them directly next to the user ids.
"""
import logging
import os
from datetime import datetime, timezone

import pymongo

log = logging.getLogger("chess.db")

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("MONGODB_DB", "szachy")

_client = None


def utcnow():
    return datetime.now(timezone.utc)


def aware(dt):
    # Make sure every datetime we compare is timezone-aware UTC
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def get_db():
    global _client
    if _client is None:
        if MONGODB_URI:
            _client = pymongo.MongoClient(MONGODB_URI, tz_aware=True, serverSelectionTimeoutMS=10000)
        else:
            import mongomock
            log.warning("MONGODB_URI not set - using an in-memory database (data is lost on restart)")
            _client = mongomock.MongoClient(tz_aware=True)
    return _client[DB_NAME]


def init_db():
    db = get_db()
    db.users.create_index("username_lower", unique=True)
    db.sessions.create_index("user_id")
    db.sessions.create_index("expires_at", expireAfterSeconds=0)  # Mongo deletes expired sessions
    db.games.create_index([("status", 1), ("created_at", -1)])
    db.games.create_index([("white_id", 1), ("status", 1)])
    db.games.create_index([("black_id", 1), ("status", 1)])
    db.games.create_index("creator_id")
    return db


def reset_for_tests():
    global _client
    _client = None
