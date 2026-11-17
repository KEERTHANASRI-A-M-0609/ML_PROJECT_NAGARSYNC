"""
backend/app/auth.py — Password hashing, JWT tokens, role-based access.
No plain-text passwords. Roles enforced server-side.
"""
from __future__ import annotations

import os
import secrets
import time
import uuid
import hashlib
import hmac
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET = os.getenv("JWT_SECRET") or secrets.token_urlsafe(48)
ALGO = "HS256"
TTL = 60 * 60 * 24 * 7  # 7 days

bearer = HTTPBearer(auto_error=False)

ROLES = {"citizen", "admin", "field_worker"}


# ── Minimal JWT (no external lib needed) ─────────────────────────────────

import base64, json as _json


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _sign(payload: dict) -> str:
    header = _b64url(_json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64url(_json.dumps(payload).encode())
    sig = hmac.new(SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{_b64url(sig)}"


def _verify(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, body, sig = parts
        decoded_header = _json.loads(base64.urlsafe_b64decode(header + "=" * (-len(header) % 4)))
        if decoded_header.get("alg") != ALGO or decoded_header.get("typ") != "JWT":
            return None
        expected = _b64url(
            hmac.new(SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig, expected):
            return None
        pad = -len(body) % 4
        payload = _json.loads(base64.urlsafe_b64decode(body + "=" * pad))
        if payload.get("exp", 0) < time.time() or not all(
            isinstance(payload.get(key), str) and payload[key]
            for key in ("sub", "email", "role", "name")
        ):
            return None
        return payload
    except Exception:
        return None


def create_token(user_id: str, email: str, role: str, name: str, token_version: int = 0) -> str:
    return _sign({
        "sub": user_id,
        "email": email,
        "role": role,
        "name": name,
        "ver": token_version,
        "iat": int(time.time()),
        "exp": int(time.time()) + TTL,
    })


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000)
    return f"{salt}:{h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split(":", 1)
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000)
        return hmac.compare_digest(check.hex(), h)
    except Exception:
        return False


# ── FastAPI dependency ────────────────────────────────────────────────────

def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> dict:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = _verify(creds.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    from backend.app.users import get_user_by_id

    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account no longer exists")
    if user.get("archived_at") is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is archived")
    if int(payload.get("ver", -1)) != int(user.get("token_version", 0)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session has been revoked")
    if user.get("role") not in ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account role is invalid")
    return {
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "name": user["name"],
    }


def require_role(*roles: str):
    def dep(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return dep


require_admin = require_role("admin")
require_field = require_role("admin", "field_worker")
require_any = get_current_user
