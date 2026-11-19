"""Accounts: password hashing (scrypt from the standard library) and cookie sessions."""
import hashlib
import hmac
import os
import re
import secrets
from datetime import timedelta

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from .db import aware, get_db, utcnow

SESSION_COOKIE = "session"
SESSION_DAYS = 30
USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,20}$")
MIN_PASSWORD = 6

# scrypt parameters (n=2^14, r=8, p=1) as recommended for interactive logins
_N, _R, _P = 2 ** 14, 8, 1


class UsernameTaken(Exception):
    pass


def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    if not stored:
        return False  # guest accounts have no password
    try:
        _, n, r, p, salt, digest = stored.split("$")
        candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt),
                                   n=int(n), r=int(r), p=int(p), dklen=32)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate.hex(), digest)


def _token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def validate_new_account(username, password):
    if not isinstance(username, str) or not USERNAME_RE.match(username):
        return "Nazwa użytkownika: 3–20 znaków, litery, cyfry, _ lub -."
    if username.lower().startswith("gosc-"):
        return "Nazwy zaczynające się od „Gosc-” są zarezerwowane dla gości."
    if not isinstance(password, str) or len(password) < MIN_PASSWORD:
        return f"Hasło musi mieć co najmniej {MIN_PASSWORD} znaków."
    if len(password) > 128:
        return "Hasło jest za długie."
    return None


def create_user(username, password):
    user = {"username": username, "username_lower": username.lower(),
            "password_hash": hash_password(password), "created_at": utcnow()}
    try:
        user["_id"] = get_db().users.insert_one(user).inserted_id
    except DuplicateKeyError:
        raise UsernameTaken()
    return user


def create_guest():
    """A throwaway account for someone who opened a game link without logging in.
    It has no password, so nobody can log into it later - the session cookie is the key."""
    for _ in range(20):
        username = f"Gosc-{secrets.randbelow(90000) + 10000}"
        user = {"username": username, "username_lower": username.lower(), "password_hash": "",
                "guest": True, "created_at": utcnow()}
        try:
            user["_id"] = get_db().users.insert_one(user).inserted_id
            return user
        except DuplicateKeyError:
            continue
    raise RuntimeError("Could not pick a free guest name")


def find_user(username):
    return get_db().users.find_one({"username_lower": username.lower()})


def get_user(user_id):
    try:
        return get_db().users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None


def create_session(user):
    token = secrets.token_urlsafe(32)
    get_db().sessions.insert_one({"_id": _token_hash(token), "user_id": str(user["_id"]),
                                  "expires_at": utcnow() + timedelta(days=SESSION_DAYS)})
    return token


def user_from_token(token):
    """The logged-in user as {"id": str, "username": str}, or None."""
    if not token:
        return None
    db = get_db()
    session = db.sessions.find_one({"_id": _token_hash(token)})
    if session is None:
        return None
    if aware(session["expires_at"]) < utcnow():
        db.sessions.delete_one({"_id": session["_id"]})
        return None
    user = get_user(session["user_id"])
    if user is None:
        return None
    return {"id": str(user["_id"]), "username": user["username"], "guest": bool(user.get("guest"))}


def delete_session(token):
    if token:
        get_db().sessions.delete_one({"_id": _token_hash(token)})
