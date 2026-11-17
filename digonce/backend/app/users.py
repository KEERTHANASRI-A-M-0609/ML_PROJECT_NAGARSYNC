"""
backend/app/users.py — User registration, login, profile.
MongoDB with JSON file fallback.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from threading import Lock

from ml.config import REPORTS_DIR
from backend.app.db import get_db
from backend.app.auth import hash_password, verify_password, create_token

import re

_STORE = REPORTS_DIR / "users.json"
_LOCK = Lock()
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
_PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{16,200}$")


def _validate_email(email: str) -> str | None:
    e = (email or "").lower().strip()
    if not e or len(e) > 200 or not _EMAIL_RE.match(e):
        return "A valid email address is required"
    return None


def _validate_password(password: str) -> str | None:
    if not _PASSWORD_RE.match(password or ""):
        return "Password must be at least 16 characters and include uppercase, lowercase, number, and special character"
    return None

def _col():
    db = get_db()
    return db["users"] if db is not None else None


def _file_load() -> list[dict]:
    if not _STORE.exists():
        return []
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _file_save(items: list[dict]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    _STORE.write_text(json.dumps(items, indent=2), encoding="utf-8")


def _create_user(email: str, password: str, role: str, name: str) -> dict:
    user = {
        "id": str(uuid.uuid4()),
        "email": email.lower().strip(),
        "password_hash": hash_password(password),
        "role": role,
        "name": name.strip(),
        "token_version": 0,
        "created_at": time.time(),
    }
    col = _col()
    if col is not None:
        col.insert_one(dict(user))
    else:
        items = _file_load()
        items.append(user)
        _file_save(items)
    return user


def register(email: str, password: str, role: str, name: str) -> dict | str:
    """Public self-registration is restricted to citizen accounts."""
    if role != "citizen":
        return "Public registration can only create citizen accounts"
    result = create_managed_user(email, password, "citizen", name)
    if isinstance(result, str):
        return result
    return {"user": result["user"]}


def create_managed_user(email: str, password: str, role: str, name: str) -> dict | str:
    """Create an account after the caller has authorized its role."""
    email = (email or "").lower().strip()
    if role not in ("citizen", "admin", "field_worker"):
        return "Invalid role"
    email_err = _validate_email(email)
    if email_err:
        return email_err
    pw_err = _validate_password(password or "")
    if pw_err:
        return pw_err
    if not (name or "").strip():
        return "Name is required"
    col = _col()
    if col is not None:
        if col.find_one({"email": email}):
            return "Email already registered"
    else:
        with _LOCK:
            items = _file_load()
            if any(u["email"] == email for u in items):
                return "Email already registered"
    user = _create_user(email, password, role, name)
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    token = create_token(user["id"], user["email"], user["role"], user["name"], user["token_version"])
    return {"user": safe, "token": token}


def bootstrap_admin(email: str, password: str, name: str, bootstrap_key: str) -> dict | str:
    """Provision the first admin only when the configured one-time bootstrap key matches."""
    import os
    import hmac

    expected = os.getenv("NAGARSYNC_BOOTSTRAP_KEY")
    if not expected or not hmac.compare_digest(bootstrap_key, expected):
        return "Bootstrap is not configured or the key is invalid"
    col = _col()
    if col is not None:
        if col.find_one({"role": "admin"}):
            return "An administrator already exists"
    else:
        with _LOCK:
            if any(u.get("role") == "admin" for u in _file_load()):
                return "An administrator already exists"
    result = create_managed_user(email, password, "admin", name)
    if isinstance(result, str):
        return result
    return {"user": result["user"]}


def login(email: str, password: str, expected_role: str | None = None) -> dict | str:
    """Returns {user, token} or error string."""
    email = email.lower().strip()
    col = _col()
    user = None
    if col is not None:
        user = col.find_one({"email": email}, {"_id": 0})
    else:
        with _LOCK:
            items = _file_load()
            user = next((u for u in items if u["email"] == email), None)
    if not user or not verify_password(password, user.get("password_hash", "")):
        return "Invalid email or password"
    if user.get("archived_at") is not None:
        return "This account is archived"
    if expected_role and user.get("role") != expected_role:
        return "Invalid email or password for the selected portal"
    safe = {k: v for k, v in user.items() if k != "password_hash"}
    token = create_token(user["id"], user["email"], user["role"], user["name"], int(user.get("token_version", 0)))
    return {"user": safe, "token": token}


def revoke_tokens(user_id: str) -> bool:
    col = _col()
    if col is not None:
        result = col.update_one({"id": user_id}, {"$inc": {"token_version": 1}})
        return result.matched_count == 1
    with _LOCK:
        items = _file_load()
        for user in items:
            if user["id"] == user_id:
                user["token_version"] = int(user.get("token_version", 0)) + 1
                _file_save(items)
                return True
    return False


def get_user_by_id(user_id: str) -> dict | None:
    col = _col()
    if col is not None:
        u = col.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
        return u
    with _LOCK:
        items = _file_load()
        u = next((x for x in items if x["id"] == user_id), None)
        if u:
            return {k: v for k, v in u.items() if k != "password_hash"}
    return None


def get_user_by_email(email: str) -> dict | None:
    email = email.lower().strip()
    col = _col()
    if col is not None:
        return col.find_one({"email": email}, {"_id": 0, "password_hash": 0})
    with _LOCK:
        items = _file_load()
    user = next((item for item in items if item["email"] == email), None)
    if user:
        return {key: value for key, value in user.items() if key != "password_hash"}
    return None


def list_users(limit: int = 100, include_archived: bool = False) -> list[dict]:
    col = _col()
    if col is not None:
        users = list(col.find({}, {"_id": 0, "password_hash": 0}).limit(limit * 2))
        if not include_archived:
            users = [user for user in users if user.get("archived_at") is None]
        return users[:limit]
    with _LOCK:
        items = _file_load()
    if not include_archived:
        items = [user for user in items if user.get("archived_at") is None]
    return [{k: v for k, v in u.items() if k != "password_hash"} for u in items[:limit]]


def active_admin_count() -> int:
    col = _col()
    if col is not None:
        return col.count_documents({"role": "admin", "archived_at": None})
    with _LOCK:
        items = _file_load()
    return sum(1 for user in items if user.get("role") == "admin" and user.get("archived_at") is None)


def update_managed_user(user_id: str, name: str | None = None, role: str | None = None, password: str | None = None) -> dict | None:
    updates: dict = {}
    if name is not None:
        if not name.strip():
            return None
        updates["name"] = name.strip()
    if role is not None:
        if role not in ("citizen", "admin", "field_worker"):
            return None
        updates["role"] = role
    if password is not None:
        if _validate_password(password):
            return None
        updates["password_hash"] = hash_password(password)
    if not updates:
        return get_user_by_id(user_id)
    col = _col()
    if col is not None:
        from pymongo import ReturnDocument
        user = col.find_one_and_update(
            {"id": user_id, "archived_at": None},
            {"$set": updates, "$inc": {"token_version": 1}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0, "password_hash": 0},
        )
        return user
    with _LOCK:
        items = _file_load()
        for user in items:
            if user["id"] == user_id and user.get("archived_at") is None:
                user.update(updates)
                user["token_version"] = int(user.get("token_version", 0)) + 1
                _file_save(items)
                return {k: v for k, v in user.items() if k != "password_hash"}
    return None


def users_for_area_roles(district: str | None = None) -> list[dict]:
    """Return active admin and field_worker accounts to notify for an area event."""
    col = _col()
    roles = {"admin", "field_worker"}
    users: list[dict]
    if col is not None:
        users = list(col.find({"role": {"$in": list(roles)}}, {"_id": 0, "password_hash": 0}).limit(500))
    else:
        with _LOCK:
            items = _file_load()
        users = [{k: v for k, v in u.items() if k != "password_hash"} for u in items if u.get("role") in roles]
    active = [u for u in users if u.get("archived_at") is None and u.get("id")]
    if district:
        d = str(district).strip().lower()
        scoped = [u for u in active if str(u.get("district", "")).strip().lower() == d]
        if scoped:
            return scoped
    return active


def set_user_archived(user_id: str, archived: bool) -> dict | None:
    col = _col()
    if col is not None:
        from pymongo import ReturnDocument
        return col.find_one_and_update(
            {"id": user_id},
            {"$set": {"archived_at": time.time() if archived else None}, "$inc": {"token_version": 1}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0, "password_hash": 0},
        )
    with _LOCK:
        items = _file_load()
        for user in items:
            if user["id"] == user_id:
                user["archived_at"] = time.time() if archived else None
                user["token_version"] = int(user.get("token_version", 0)) + 1
                _file_save(items)
                return {k: v for k, v in user.items() if k != "password_hash"}
    return None
