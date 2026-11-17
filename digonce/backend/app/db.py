"""MongoDB connection for NagarSync (soft-fail if Atlas unreachable)."""
from __future__ import annotations

import os
import time

from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("MONGO_DB_NAME", "digonce")
_client = None
_last_error: str | None = None
_failed_uri: str | None = None
_failed_at: float | None = None
_RETRY_INTERVAL_SECONDS = 30


def get_client():
    global _client, _last_error, _failed_uri, _failed_at
    if _client is not None:
        return _client
    uri = os.getenv("MONGODB_URI")
    if not uri:
        _last_error = "MONGODB_URI missing"
        return None
    if (
        uri == _failed_uri
        and _failed_at is not None
        and time.monotonic() - _failed_at < _RETRY_INTERVAL_SECONDS
    ):
        return None
    try:
        from pymongo import MongoClient
        client = MongoClient(uri, serverSelectionTimeoutMS=8000)
        client.admin.command("ping")
        _client = client
        _last_error = None
        _failed_uri = None
        _failed_at = None
        return _client
    except Exception as exc:
        _last_error = str(exc)
        _failed_uri = uri
        _failed_at = time.monotonic()
        _client = None
        return None


def get_db():
    client = get_client()
    return client[DB_NAME] if client is not None else None


def feedback_col():
    db = get_db()
    return db["feedback"] if db is not None else None


def ping() -> bool:
    return get_client() is not None


def last_error() -> str | None:
    return _last_error
