"""
app/auth/dependencies.py

FastAPI dependency injectors for user authentication and session resolution.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status

from app.auth.security import get_user_by_token
from app.config import SESSION_COOKIE_NAME
from app.database import get_db


def extract_token_from_request(request: Request) -> Optional[str]:
    """
    Extracts session token from Authorization header (Bearer) or session cookie.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header:
        parts = auth_header.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]

    # Fallback to session cookie
    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    return None


def get_current_user(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db)
) -> Dict[str, Any]:
    """
    FastAPI dependency ensuring request has a valid, active session token.
    Raises 401 Unauthorized if token is missing, invalid, or expired.
    """
    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentificering påkrævet. Log venligst ind eller start en gæstesession.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_token(conn, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ugyldig eller udløbet session. Log venligst ind igen.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Denne brugerkonto er deaktiveret.",
        )

    return user


def get_optional_user(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency that returns the current authenticated user if present,
    or None if the request is unauthenticated.
    """
    token = extract_token_from_request(request)
    if not token:
        return None

    return get_user_by_token(conn, token)
