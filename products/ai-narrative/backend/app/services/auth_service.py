from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException

from backend.app.services import persistence


SESSION_TTL_SECONDS = 60 * 60 * 8


def _hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return digest.hex()


def create_user(email: str, password: str) -> dict[str, Any]:
    salt_hex = secrets.token_hex(16)
    password_hash = _hash_password(password, salt_hex)
    return persistence.create_user(email=email, password_hash=password_hash, password_salt=salt_hex)


def verify_credentials(email: str, password: str) -> dict[str, Any] | None:
    user = persistence.get_user_by_email(email)
    if not user:
        return None

    expected_hash = _hash_password(password, user["password_salt"])
    if not secrets.compare_digest(expected_hash, user["password_hash"]):
        return None

    if not user.get("is_active", 1):
        raise HTTPException(status_code=403, detail="Account is deactivated.")

    return {
        "id": int(user["id"]),
        "email": user["email"],
        "is_admin": bool(user.get("is_admin", 0)),
        "is_active": bool(user.get("is_active", 1)),
    }


def create_user_session(user_id: int) -> tuple[str, int]:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL_SECONDS)).isoformat()
    persistence.create_session(token=token, user_id=user_id, expires_at=expires_at)
    return token, SESSION_TTL_SECONDS


def get_user_from_bearer_token(authorization_header: str | None) -> dict[str, Any] | None:
    if not authorization_header:
        return None

    token_type, _, token = authorization_header.partition(" ")
    if token_type.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header format.")

    user = persistence.get_user_by_session_token(token.strip())
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired access token.")

    return {
        "id": int(user["id"]),
        "email": user["email"],
        "is_admin": bool(user.get("is_admin", 0)),
        "is_active": bool(user.get("is_active", 1)),
    }


def require_authenticated_user(authorization_header: str | None) -> dict[str, Any]:
    user = get_user_from_bearer_token(authorization_header)
    if not user:
        raise HTTPException(status_code=401, detail="Authorization required.")
    return user


def require_admin_user(authorization_header: str | None) -> dict[str, Any]:
    user = require_authenticated_user(authorization_header)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user