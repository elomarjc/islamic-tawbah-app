"""
app/auth/security.py

Zero-dependency cryptographically secure password hashing, session tokens,
and data isolation/cascading deletion primitives using Python standard library.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.config import (
    PBKDF2_ALGORITHM,
    PBKDF2_ITERATIONS,
    PBKDF2_SALT_BYTES,
    REGISTERED_SESSION_DAYS,
    GUEST_SESSION_DAYS,
)


def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using PBKDF2-HMAC-SHA256 with 100,000 iterations.
    Format: 'pbkdf2_sha256$100000$<salt_hex>$<hash_hex>'
    """
    if not password:
        raise ValueError("Password cannot be empty.")
    salt = secrets.token_bytes(PBKDF2_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against the stored PBKDF2 hash using constant-time comparison.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4 or parts[0] != PBKDF2_ALGORITHM:
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        stored_hash = bytes.fromhex(parts[3])

        computed_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(computed_hash, stored_hash)
    except Exception:
        return False


def create_session_token() -> str:
    """
    Generates a cryptographically strong 256-bit URL-safe token.
    """
    return secrets.token_urlsafe(32)


def create_session(
    conn: sqlite3.Connection,
    user_id: str,
    is_guest: bool = False,
    ttl_days: Optional[int] = None
) -> str:
    """
    Persists a new session token in SQLite for the given user.
    """
    token = create_session_token()
    now = datetime.now(timezone.utc)
    if ttl_days is None:
        ttl_days = GUEST_SESSION_DAYS if is_guest else REGISTERED_SESSION_DAYS
    expires_at = now + timedelta(days=ttl_days)

    now_iso = now.isoformat()
    exp_iso = expires_at.isoformat()
    guest_int = 1 if is_guest else 0

    cursor = conn.cursor()
    # Write to both user_sessions and sessions for schema compatibility
    cursor.execute(
        """
        INSERT INTO user_sessions (token, user_id, created_at, expires_at, is_guest)
        VALUES (?, ?, ?, ?, ?)
        """,
        (token, user_id, now_iso, exp_iso, guest_int)
    )
    cursor.execute(
        """
        INSERT INTO sessions (token, user_id, created_at, expires_at, is_guest)
        VALUES (?, ?, ?, ?, ?)
        """,
        (token, user_id, now_iso, exp_iso, guest_int)
    )
    conn.commit()
    return token


def get_user_by_token(conn: sqlite3.Connection, token: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the user associated with an active, unexpired session token.
    Automatically purges expired tokens.
    """
    if not token:
        return None

    now_iso = datetime.now(timezone.utc).isoformat()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT u.id, u.username, u.email, u.is_guest, u.is_active, s.expires_at, s.token
        FROM user_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ?
        """,
        (token,)
    )
    row = cursor.fetchone()
    if not row:
        return None

    # Check expiration
    if row["expires_at"] < now_iso:
        cursor.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"] if "email" in row.keys() else None,
        "is_guest": bool(row["is_guest"]),
        "is_active": bool(row["is_active"]) if "is_active" in row.keys() else True,
        "token": row["token"]
    }


def revoke_session(conn: sqlite3.Connection, token: str) -> bool:
    """
    Immediately revokes and deletes a session token.
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    return cursor.rowcount > 0


def create_guest_user(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Creates an anonymous, low-friction guest user account with an active session.
    """
    guest_id = f"guest_{uuid.uuid4().hex}"
    guest_name = f"Gæst-{secrets.token_hex(3)}"
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (id, username, password_hash, is_guest, is_active, created_at)
        VALUES (?, ?, '', 1, 1, ?)
        """,
        (guest_id, guest_name, now_iso)
    )
    conn.commit()

    token = create_session(conn, guest_id, is_guest=True)
    return {
        "id": guest_id,
        "username": guest_name,
        "is_guest": True,
        "token": token
    }


def delete_confession(conn: sqlite3.Connection, confession_id: str, user_id: str) -> bool:
    """
    Granular deletion of a single confession and its cascaded incidents and action items.
    Also unlinks physical audio recording from disk if present.
    Strictly scoped to user_id to prevent IDOR.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT audio_path FROM confessions WHERE id = ? AND user_id = ?",
        (confession_id, user_id)
    )
    row = cursor.fetchone()
    if not row:
        return False

    audio_path = row["audio_path"]
    if audio_path and os.path.exists(audio_path):
        try:
            os.remove(audio_path)
        except OSError:
            pass  # Windows file lock or already unlinked

    # SQLite ON DELETE CASCADE handles incidents and action_items
    cursor.execute(
        "DELETE FROM confessions WHERE id = ? AND user_id = ?",
        (confession_id, user_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_journal_entry(conn: sqlite3.Connection, entry_id: str, user_id: str) -> bool:
    """
    Granular deletion of a single repentance journal reflection.
    Strictly scoped to user_id.
    """
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM journal_entries WHERE id = ? AND user_id = ?",
        (entry_id, user_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def wipe_user_data(
    conn: sqlite3.Connection,
    user_id: str,
    delete_account: bool = False
) -> Dict[str, Any]:
    """
    Panic Wipe: Purges all confessions, incidents, action items, journal reflections,
    and audio recordings belonging to the user.
    If delete_account is True or if user is a guest, also purges user record and sessions.
    """
    cursor = conn.cursor()

    # 1. Physical media unlinking
    cursor.execute(
        "SELECT audio_path FROM confessions WHERE user_id = ? AND audio_path IS NOT NULL",
        (user_id,)
    )
    for row in cursor.fetchall():
        path = row["audio_path"]
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    # 2. Count before deletion
    cursor.execute("SELECT count(*) FROM confessions WHERE user_id = ?", (user_id,))
    c_count = cursor.fetchone()[0]

    cursor.execute("SELECT count(*) FROM journal_entries WHERE user_id = ?", (user_id,))
    j_count = cursor.fetchone()[0]

    # Check if guest
    is_guest = False
    cursor.execute("SELECT is_guest FROM users WHERE id = ?", (user_id,))
    u_row = cursor.fetchone()
    if u_row:
        is_guest = bool(u_row["is_guest"])

    if delete_account or is_guest:
        # Cascades to user_sessions, sessions, confessions, incidents, action_items, journal_entries
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    else:
        # Registered user wiping repentance history while preserving login account
        cursor.execute("DELETE FROM confessions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM journal_entries WHERE user_id = ?", (user_id,))

    conn.commit()

    return {
        "status": "success",
        "message": "Al historik, handlinger og personlige opgørelser er blevet permanent slettet.",
        "confessions_purged": c_count,
        "journal_purged": j_count,
        "account_deleted": delete_account or is_guest
    }
