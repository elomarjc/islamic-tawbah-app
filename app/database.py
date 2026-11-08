"""
app/database.py

Thread-safe SQLite connection manager with WAL mode, foreign key enforcement,
automatic schema migration, and demo account seeding.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Optional

from app.config import DB_PATH, DATA_DIR


def configure_connection(conn: sqlite3.Connection) -> sqlite3.Connection:
    """
    Configures an SQLite connection with WAL mode, foreign keys, and busy timeout.
    Must be called on every newly established SQLite connection.
    """
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("PRAGMA busy_timeout = 5000;")
    cursor.execute("PRAGMA foreign_keys = ON;")
    try:
        current_jm = cursor.execute("PRAGMA journal_mode;").fetchone()[0]
        if str(current_jm).lower() != "wal":
            cursor.execute("PRAGMA journal_mode = WAL;")
    except sqlite3.OperationalError:
        pass
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.close()
    return conn


@contextmanager
def get_db_connection(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Thread-safe context manager providing an active SQLite connection.
    Automatically commits on normal exit and rolls back on exception.
    """
    target_path = db_path or DB_PATH
    if target_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

    conn = sqlite3.connect(
        target_path,
        check_same_thread=False,
        timeout=10.0
    )
    configure_connection(conn)
    try:
        yield conn
        if conn.in_transaction:
            conn.commit()
    except Exception:
        if conn.in_transaction:
            try:
                conn.rollback()
            except sqlite3.OperationalError:
                pass
        raise
    finally:
        conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI dependency that yields a managed SQLite database connection.
    """
    with get_db_connection() as conn:
        yield conn


SCHEMA_DDL = """
-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    is_guest INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_login TEXT
);

-- 2. USER SESSIONS TABLE (For Stateful Session Auth)
CREATE TABLE IF NOT EXISTS user_sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    is_guest INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Compatibility alias for sessions
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    is_guest INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. CONFESSIONS TABLE
CREATE TABLE IF NOT EXISTS confessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    raw_input_type TEXT NOT NULL CHECK(raw_input_type IN ('text', 'voice')),
    raw_text TEXT NOT NULL,
    transcript TEXT,
    audio_path TEXT,
    consent_given INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'completed' CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
    summary TEXT,
    sin_classification TEXT CHECK(sin_classification IN ('huqooq_allah', 'huqooq_al_ibad', 'both')),
    confidence_level TEXT CHECK(confidence_level IN ('high', 'medium', 'low')),
    scholar_consultation_required INTEGER NOT NULL DEFAULT 0,
    analysis_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. INCIDENTS TABLE
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    confession_id TEXT NOT NULL,
    incident_order INTEGER NOT NULL DEFAULT 1,
    incident_title TEXT NOT NULL,
    sin_classification TEXT NOT NULL CHECK(sin_classification IN ('huqooq_allah', 'huqooq_al_ibad', 'both')),
    description TEXT NOT NULL,
    affected_parties TEXT NOT NULL DEFAULT '[]',
    allah_rights TEXT NOT NULL DEFAULT '[]',
    people_rights TEXT NOT NULL DEFAULT '[]',
    apology_guidance TEXT,
    restitution_guidance TEXT,
    severity_explanation TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (confession_id) REFERENCES confessions(id) ON DELETE CASCADE
);

-- 5. ACTION ITEMS TABLE (With user_id for Defense-in-Depth IDOR protection)
CREATE TABLE IF NOT EXISTS action_items (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    confession_id TEXT NOT NULL,
    incident_id TEXT,
    category TEXT NOT NULL,
    action_type TEXT,
    title TEXT,
    description TEXT NOT NULL,
    explanation TEXT,
    target_party TEXT,
    completed INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (confession_id) REFERENCES confessions(id) ON DELETE CASCADE,
    FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 6. RECENT JOURNAL ENTRIES TABLE (Spiritual Reflections / Muhasabah)
CREATE TABLE IF NOT EXISTS journal_entries (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- PERFORMANCE & QUERY ACCELERATION INDEXES
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_compat_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_compat_sessions_exp ON sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_confessions_user_created ON confessions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_confessions_status ON confessions(status);

CREATE INDEX IF NOT EXISTS idx_incidents_confession ON incidents(confession_id);
CREATE INDEX IF NOT EXISTS idx_incidents_classification ON incidents(sin_classification);

CREATE INDEX IF NOT EXISTS idx_actions_user_status ON action_items(user_id, completed, category);
CREATE INDEX IF NOT EXISTS idx_actions_confession ON action_items(confession_id);
CREATE INDEX IF NOT EXISTS idx_actions_incident ON action_items(incident_id);

CREATE INDEX IF NOT EXISTS idx_journal_user_created ON journal_entries(user_id, created_at DESC);
"""


def seed_demo_account(conn: sqlite3.Connection) -> None:
    """
    Seeds a default demo account with sample data for immediate development testing.
    Idempotent and resilient against concurrent multi-process initialization.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = 'demo'")
    if cursor.fetchone():
        return

    from app.auth.security import hash_password

    now_iso = datetime.now(timezone.utc).isoformat()
    demo_user_id = "user_demo_default"
    demo_pw_hash = hash_password("demo123")

    try:
        # Insert demo user
        cursor.execute(
            """
            INSERT OR IGNORE INTO users (id, username, email, password_hash, is_guest, is_active, created_at)
            VALUES (?, 'demo', 'demo@tawbah.app', ?, 0, 1, ?)
            """,
            (demo_user_id, demo_pw_hash, now_iso)
        )

        # Insert demo session token
        demo_token = "demo_session_token_123456789"
        cursor.execute(
            """
            INSERT OR IGNORE INTO user_sessions (token, user_id, created_at, expires_at, is_guest)
            VALUES (?, ?, ?, '2099-12-31T23:59:59Z', 0)
            """,
            (demo_token, demo_user_id, now_iso)
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO sessions (token, user_id, created_at, expires_at, is_guest)
            VALUES (?, ?, ?, '2099-12-31T23:59:59Z', 0)
            """,
            (demo_token, demo_user_id, now_iso)
        )

        # Seed 1 sample confession (Ghibah / Backbiting scenario)
        conf_id = "conf_demo_1"
        cursor.execute(
            """
            INSERT OR IGNORE INTO confessions (
                id, user_id, raw_input_type, raw_text, consent_given, status,
                summary, sin_classification, confidence_level, scholar_consultation_required, created_at
            ) VALUES (
                ?, ?, 'text', 'Jeg kom til at tale dårligt om min kollega bag hans ryg til vores chef.', 1, 'completed',
                'Baktalelse af kollega overfor chefen.', 'both', 'high', 0, ?
            )
            """,
            (conf_id, demo_user_id, now_iso)
        )

        inc_id = "inc_demo_1"
        cursor.execute(
            """
            INSERT OR IGNORE INTO incidents (
                id, confession_id, incident_order, incident_title, sin_classification, description,
                affected_parties, allah_rights, people_rights, apology_guidance, restitution_guidance, created_at
            ) VALUES (
                ?, ?, 1, 'Baktalelse af kollega (Ghibah)', 'both',
                'Baktalelse overtræder både Allahs forbud og kollegaens ære.',
                '["Kollega", "Chef"]', '["Overtrædelse af forbud mod ghibah"]', '["Kollegaens ære og omdømme"]',
                'Hvis kollegaen allerede ved det, bed om tilgivelse. Hvis ikke, tal godt om vedkommende overfor chefen for at rette misforståelsen uden at skabe større splid.',
                'Opret genoprejsning ved at rose kollegaens gode egenskaber.', ?
            )
            """,
            (inc_id, conf_id, now_iso)
        )

        cursor.execute(
            """
            INSERT OR IGNORE INTO action_items (
                id, user_id, confession_id, incident_id, category, action_type, title,
                description, explanation, target_party, completed, created_at
            ) VALUES 
            ('act_demo_1', ?, ?, ?, 'wajib', 'tawbah_allah', 'Oprigtig Tawbah',
             'Sincere Tawbah med nadam (anger) og stop baktalelse',
             'Ophør med at omtale kollegaen negativt og bed Allah om tilgivelse.', 'Allah', 1, ?),
            ('act_demo_2', ?, ?, ?, 'wajib', 'rectification', 'Ret udtalelser',
             'Ret misvisende udtalelser over for chefen',
             'Tal sandt og positivt om kollegaen overfor chefen for at beskytte hans ære.', 'Kollega', 0, ?),
            ('act_demo_3', ?, ?, ?, 'mustahabb', 'dua', 'Dua for den bagtalte',
             'Gør dua for kollegaen i dine bønner',
             'Bed om Allahs tilgivelse og velsignelse for den person, du har baktalt.', 'Kollega', 0, ?)
            """,
            (demo_user_id, conf_id, inc_id, now_iso,
             demo_user_id, conf_id, inc_id, now_iso,
             demo_user_id, conf_id, inc_id, now_iso)
        )

        cursor.execute(
            """
            INSERT OR IGNORE INTO journal_entries (id, user_id, title, content, tags, created_at)
            VALUES ('jnl_demo_1', ?, 'Refleksion over tungens vogtning',
                    'I dag mindede jeg mig selv om hadithen om at den, der tror på Allah og den Sidste Dag, skal sige noget godt eller tie stille.',
                    '["tungen", "istighfar", "selvkontrol"]', ?)
            """,
            (demo_user_id, now_iso)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        if conn.in_transaction:
            try:
                conn.rollback()
            except sqlite3.OperationalError:
                pass


def init_db(db_path: Optional[str] = None) -> None:
    """
    Initializes the database schema and seeds the default demo account.
    Safe to run repeatedly (uses CREATE TABLE IF NOT EXISTS).
    """
    target_path = db_path or DB_PATH
    if target_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

    with get_db_connection(target_path) as conn:
        conn.executescript(SCHEMA_DDL)
        seed_demo_account(conn)
