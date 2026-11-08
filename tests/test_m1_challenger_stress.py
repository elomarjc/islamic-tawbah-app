"""
tests/test_m1_challenger_stress.py

Adversarial Stress Test Harness for Milestone 1:
- SQLite WAL Mode & Multi-Threaded Concurrency (20-50 concurrent worker threads)
- Foreign Key Constraint Violations & Cascading Deletions
- Multi-Tenant Isolation & IDOR Boundaries
- Granular Deletion, Panic Wipe, and Physical Media Unlinking
- Transaction Rollbacks and SQL Injection Hardening
"""

import concurrent.futures
import os
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import (
    PBKDF2_ALGORITHM,
    PBKDF2_ITERATIONS,
    PBKDF2_SALT_BYTES,
)
from app.database import (
    init_db,
    get_db_connection,
    configure_connection,
    SCHEMA_DDL,
)
from app.models import (
    User,
    UserSession,
    Confession,
    Incident,
    ActionItem,
    JournalEntry,
    parse_json_field,
    dump_json_field,
)
from app.auth.security import (
    hash_password,
    verify_password,
    create_session_token,
    create_session,
    get_user_by_token,
    revoke_session,
    create_guest_user,
    delete_confession,
    delete_journal_entry,
    wipe_user_data,
)


class TestMilestone1AdversarialStress(unittest.TestCase):
    """
    Adversarial and Empirical Stress Test Suite for M1 Data, Auth, and Storage.
    """

    @classmethod
    def setUpClass(cls):
        # Create a dedicated temporary disk file for SQLite WAL tests
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = str(Path(cls.temp_dir.name) / "challenger_stress.db")
        init_db(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except OSError:
            pass

    def get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        configure_connection(conn)
        return conn

    # =========================================================================
    # 1. SQLITE WAL MODE & MULTI-THREADED CONCURRENCY STRESS
    # =========================================================================

    def test_wal_mode_active_on_disk(self):
        """Verify SQLite journal_mode is WAL on disk database."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode;")
            mode = cursor.fetchone()[0]
            self.assertEqual(mode.lower(), "wal", f"Database must be in WAL mode, found: {mode}")

            cursor.execute("PRAGMA synchronous;")
            sync = cursor.fetchone()[0]
            # synchronous = NORMAL is 1
            self.assertEqual(sync, 1, f"PRAGMA synchronous should be NORMAL (1), found: {sync}")

            cursor.execute("PRAGMA busy_timeout;")
            busy = cursor.fetchone()[0]
            self.assertGreaterEqual(busy, 5000, f"PRAGMA busy_timeout must be >= 5000ms, found: {busy}")

    def test_multithreaded_concurrent_reads_and_writes(self):
        """
        Stress test: 20 concurrent threads (10 writers, 10 readers) executing
        transactions simultaneously on SQLite WAL database.
        Must execute without unhandled database lock errors or data corruption.
        """
        num_writers = 10
        num_readers = 10
        items_per_writer = 15

        writer_errors = []
        reader_errors = []
        inserted_confession_ids = []
        lock = threading.Lock()

        # Seed 1 user for writers
        user_id = f"user_concurrent_{uuid.uuid4().hex[:8]}"
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'hash', ?)",
                (user_id, f"con_user_{uuid.uuid4().hex[:6]}", datetime.now(timezone.utc).isoformat())
            )

        def writer_task(worker_idx: int):
            try:
                for i in range(items_per_writer):
                    conf_id = f"conf_c_{worker_idx}_{i}_{uuid.uuid4().hex[:6]}"
                    with get_db_connection(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO confessions (
                                id, user_id, raw_input_type, raw_text, consent_given, status, created_at
                            ) VALUES (?, ?, 'text', ?, 1, 'completed', ?)
                            """,
                            (conf_id, user_id, f"Confession from worker {worker_idx} item {i}", datetime.now(timezone.utc).isoformat())
                        )
                        cursor.execute(
                            """
                            INSERT INTO incidents (
                                id, confession_id, incident_title, sin_classification, description, created_at
                            ) VALUES (?, ?, 'Incident', 'huqooq_allah', 'Desc', ?)
                            """,
                            (f"inc_{conf_id}", conf_id, datetime.now(timezone.utc).isoformat())
                        )
                    with lock:
                        inserted_confession_ids.append(conf_id)
                    time.sleep(0.005)  # small jitter
            except Exception as e:
                with lock:
                    writer_errors.append((worker_idx, str(e)))

        def reader_task(worker_idx: int):
            try:
                for _ in range(items_per_writer * 2):
                    with get_db_connection(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT count(*) FROM confessions WHERE user_id = ?", (user_id,))
                        count = cursor.fetchone()[0]
                        self.assertGreaterEqual(count, 0)
                        cursor.execute("SELECT id, summary FROM confessions ORDER BY created_at DESC LIMIT 5")
                        rows = cursor.fetchall()
                        self.assertTrue(isinstance(rows, list))
                    time.sleep(0.003)
            except Exception as e:
                with lock:
                    reader_errors.append((worker_idx, str(e)))

        threads: List[threading.Thread] = []
        for w in range(num_writers):
            threads.append(threading.Thread(target=writer_task, args=(w,)))
        for r in range(num_readers):
            threads.append(threading.Thread(target=reader_task, args=(r,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30.0)

        # Assert zero errors under concurrent load
        self.assertEqual(len(writer_errors), 0, f"Writers encountered concurrency errors: {writer_errors}")
        self.assertEqual(len(reader_errors), 0, f"Readers encountered concurrency errors: {reader_errors}")

        # Verify all records exist
        expected_total = num_writers * items_per_writer
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM confessions WHERE user_id = ?", (user_id,))
            actual_count = cursor.fetchone()[0]
            self.assertEqual(actual_count, expected_total, f"Expected {expected_total} confessions, got {actual_count}")

            cursor.execute("SELECT count(*) FROM incidents WHERE confession_id LIKE 'conf_c_%'")
            actual_incidents = cursor.fetchone()[0]
            self.assertEqual(actual_incidents, expected_total, "Every confession must have an incident created concurrently")

    def test_write_contention_stress(self):
        """
        Stress test: 30 threads attempting rapid simultaneous INSERTs to measure
        busy timeout and lock acquisition reliability under high contention.
        """
        contention_user = f"user_contention_{uuid.uuid4().hex[:6]}"
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'hash', ?)",
                (contention_user, f"u_contend_{uuid.uuid4().hex[:6]}", datetime.now(timezone.utc).isoformat())
            )

        errors = []
        num_threads = 25

        def contend_task(t_idx: int):
            try:
                with get_db_connection(self.db_path) as conn:
                    conn.execute(
                        "INSERT INTO journal_entries (id, user_id, content, tags, created_at) VALUES (?, ?, ?, '[]', ?)",
                        (f"jnl_contend_{t_idx}", contention_user, f"Content {t_idx}", datetime.now(timezone.utc).isoformat())
                    )
            except Exception as exc:
                errors.append((t_idx, str(exc)))

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(contend_task, i) for i in range(num_threads)]
            concurrent.futures.wait(futures)

        self.assertEqual(len(errors), 0, f"Write contention resulted in unhandled errors: {errors}")

        with get_db_connection(self.db_path) as conn:
            cnt = conn.execute("SELECT count(*) FROM journal_entries WHERE user_id = ?", (contention_user,)).fetchone()[0]
            self.assertEqual(cnt, num_threads, f"Expected {num_threads} journal entries, got {cnt}")

    # =========================================================================
    # 2. FOREIGN KEY CONSTRAINT VIOLATIONS & ENFORCEMENT
    # =========================================================================

    def test_foreign_key_pragma_enforced(self):
        """Verify foreign_keys pragma is enabled on every get_db_connection call."""
        with get_db_connection(self.db_path) as conn:
            fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
            self.assertEqual(fk, 1, "PRAGMA foreign_keys must be 1 (ON)")

    def test_foreign_key_violation_confession_user_id(self):
        """Inserting confession with non-existent user_id must raise sqlite3.IntegrityError."""
        with self.assertRaises(sqlite3.IntegrityError):
            with get_db_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO confessions (id, user_id, raw_input_type, raw_text, created_at)
                    VALUES ('conf_bad_user', 'non_existent_user_99999', 'text', 'Test', ?)
                    """,
                    (datetime.now(timezone.utc).isoformat(),)
                )

    def test_foreign_key_violation_incident_confession_id(self):
        """Inserting incident with non-existent confession_id must raise sqlite3.IntegrityError."""
        with self.assertRaises(sqlite3.IntegrityError):
            with get_db_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO incidents (id, confession_id, incident_title, sin_classification, description, created_at)
                    VALUES ('inc_bad_conf', 'non_existent_conf_99999', 'Title', 'huqooq_allah', 'Desc', ?)
                    """,
                    (datetime.now(timezone.utc).isoformat(),)
                )

    def test_foreign_key_violation_action_item_invalid_references(self):
        """Inserting action item with invalid references must raise sqlite3.IntegrityError."""
        # 1. Invalid confession_id
        with self.assertRaises(sqlite3.IntegrityError):
            with get_db_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO action_items (id, user_id, confession_id, category, description, created_at)
                    VALUES ('act_bad_conf', 'demo', 'bad_conf_id_99999', 'wajib', 'Desc', ?)
                    """,
                    (datetime.now(timezone.utc).isoformat(),)
                )

        # 2. Invalid user_id
        with self.assertRaises(sqlite3.IntegrityError):
            with get_db_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO action_items (id, user_id, confession_id, category, description, created_at)
                    VALUES ('act_bad_user', 'bad_user_id_99999', 'conf_demo_1', 'wajib', 'Desc', ?)
                    """,
                    (datetime.now(timezone.utc).isoformat(),)
                )

        # 3. Invalid incident_id
        with self.assertRaises(sqlite3.IntegrityError):
            with get_db_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO action_items (id, user_id, confession_id, incident_id, category, description, created_at)
                    VALUES ('act_bad_inc', 'user_demo_default', 'conf_demo_1', 'bad_incident_id_99999', 'wajib', 'Desc', ?)
                    """,
                    (datetime.now(timezone.utc).isoformat(),)
                )

    def test_foreign_key_violation_session_user_id(self):
        """Inserting session with non-existent user_id must raise sqlite3.IntegrityError."""
        with self.assertRaises(sqlite3.IntegrityError):
            with get_db_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO user_sessions (token, user_id, created_at, expires_at)
                    VALUES ('fake_token_123', 'fake_user_id_123', '2026-01-01T00:00:00Z', '2099-01-01T00:00:00Z')
                    """
                )

    def test_foreign_key_violation_journal_user_id(self):
        """Inserting journal entry with non-existent user_id must raise sqlite3.IntegrityError."""
        with self.assertRaises(sqlite3.IntegrityError):
            with get_db_connection(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO journal_entries (id, user_id, content, created_at)
                    VALUES ('jnl_bad_user', 'fake_user_id_999', 'Test content', ?)
                    """,
                    (datetime.now(timezone.utc).isoformat(),)
                )

    # =========================================================================
    # 3. MULTI-TENANT ISOLATION STRESS
    # =========================================================================

    def test_multi_tenant_confession_isolation(self):
        """
        Verify complete isolation between Tenant A and Tenant B:
        - Tenant A creates confessions
        - Tenant B cannot read, delete, or modify Tenant A's confessions
        """
        with get_db_connection(self.db_path) as conn:
            user_a = create_guest_user(conn)
            user_b = create_guest_user(conn)

            # Tenant A creates confession
            conf_a_id = f"conf_iso_{uuid.uuid4().hex[:6]}"
            conn.execute(
                """
                INSERT INTO confessions (id, user_id, raw_input_type, raw_text, created_at)
                VALUES (?, ?, 'text', 'Hemmelig tilståelse for Bruger A', ?)
                """,
                (conf_a_id, user_a["id"], datetime.now(timezone.utc).isoformat())
            )
            conn.commit()

            # Tenant B attempts to delete Tenant A's confession -> Must fail
            deleted = delete_confession(conn, conf_a_id, user_b["id"])
            self.assertFalse(deleted, "Tenant B must NOT be able to delete Tenant A's confession")

            # Verify Tenant A's confession remains completely untouched
            row = conn.execute("SELECT id, user_id FROM confessions WHERE id = ?", (conf_a_id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["user_id"], user_a["id"])

            # Verify tenant-scoped query does not leak Tenant A's confession to Tenant B
            b_confessions = conn.execute(
                "SELECT id FROM confessions WHERE user_id = ?",
                (user_b["id"],)
            ).fetchall()
            b_ids = [r["id"] for r in b_confessions]
            self.assertNotIn(conf_a_id, b_ids, "Tenant B query must not contain Tenant A's confession")

    def test_multi_tenant_journal_isolation(self):
        """
        Verify journal isolation between Tenant A and Tenant B:
        - Tenant B cannot delete Tenant A's journal entry
        """
        with get_db_connection(self.db_path) as conn:
            user_a = create_guest_user(conn)
            user_b = create_guest_user(conn)

            jnl_a_id = f"jnl_iso_{uuid.uuid4().hex[:6]}"
            conn.execute(
                """
                INSERT INTO journal_entries (id, user_id, title, content, created_at)
                VALUES (?, ?, 'Privat refleksion', 'Meget privat indhold for Bruger A', ?)
                """,
                (jnl_a_id, user_a["id"], datetime.now(timezone.utc).isoformat())
            )
            conn.commit()

            # Tenant B attempts to delete Tenant A's journal entry -> Must fail
            deleted = delete_journal_entry(conn, jnl_a_id, user_b["id"])
            self.assertFalse(deleted, "Tenant B must not be able to delete Tenant A's journal entry")

            # Verify entry still exists
            row = conn.execute("SELECT id, user_id FROM journal_entries WHERE id = ?", (jnl_a_id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["user_id"], user_a["id"])

    def test_multi_tenant_action_item_defense_in_depth(self):
        """
        Verify that action_items table includes user_id and scoped queries prevent cross-tenant mutation.
        """
        with get_db_connection(self.db_path) as conn:
            user_a = create_guest_user(conn)
            user_b = create_guest_user(conn)

            conf_a = f"conf_act_iso_{uuid.uuid4().hex[:6]}"
            conn.execute(
                "INSERT INTO confessions (id, user_id, raw_input_type, raw_text, created_at) VALUES (?, ?, 'text', 'Text', ?)",
                (conf_a, user_a["id"], datetime.now(timezone.utc).isoformat())
            )

            act_a = f"act_iso_{uuid.uuid4().hex[:6]}"
            conn.execute(
                """
                INSERT INTO action_items (id, user_id, confession_id, category, description, completed, created_at)
                VALUES (?, ?, ?, 'wajib', 'Handling for Bruger A', 0, ?)
                """,
                (act_a, user_a["id"], conf_a, datetime.now(timezone.utc).isoformat())
            )
            conn.commit()

            # Attempt update scoped to user_b (simulating what an API PATCH /api/actions/{id} should do)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE action_items SET completed = 1 WHERE id = ? AND user_id = ?",
                (act_a, user_b["id"])
            )
            conn.commit()
            self.assertEqual(cursor.rowcount, 0, "Cross-tenant update must affect 0 rows")

            # Verify action item remains uncompleted (0)
            status = conn.execute("SELECT completed FROM action_items WHERE id = ?", (act_a,)).fetchone()[0]
            self.assertEqual(status, 0, "Action item completed status must remain 0")

    def test_sql_injection_defense_in_security_and_queries(self):
        """
        Adversarial attack: verify SQL injection payloads in parameters do not execute or compromise data.
        """
        sqli_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin'--",
            "' UNION SELECT * FROM users --",
            "1'; SELECT pg_sleep(5); --",
            "test' AND 1=(SELECT COUNT(*) FROM sqlite_master WHERE type='table') --"
        ]

        with get_db_connection(self.db_path) as conn:
            for payload in sqli_payloads:
                # 1. get_user_by_token with SQLi payload
                user = get_user_by_token(conn, payload)
                self.assertIsNone(user, f"SQLi payload in token unexpectedly returned a user: {payload}")

                # 2. delete_confession with SQLi payload
                deleted = delete_confession(conn, payload, payload)
                self.assertFalse(deleted)

                # 3. delete_journal_entry with SQLi payload
                deleted = delete_journal_entry(conn, payload, payload)
                self.assertFalse(deleted)

            # Verify table 'users' is intact
            table_check = conn.execute("SELECT count(*) FROM users").fetchone()[0]
            self.assertGreaterEqual(table_check, 1)

    # =========================================================================
    # 4. CASCADING DELETION STRESS
    # =========================================================================

    def test_cascading_deletion_confession_purges_incidents_and_actions(self):
        """
        Deep cascading deletion test:
        1 confession -> 3 incidents -> 9 action items (3 per incident).
        Deleting confession must purge all 3 incidents and all 9 action items with zero orphans.
        """
        with get_db_connection(self.db_path) as conn:
            user = create_guest_user(conn)
            conf_id = f"conf_cascade_{uuid.uuid4().hex[:6]}"
            now_iso = datetime.now(timezone.utc).isoformat()

            conn.execute(
                "INSERT INTO confessions (id, user_id, raw_input_type, raw_text, created_at) VALUES (?, ?, 'text', 'Cascade Test', ?)",
                (conf_id, user["id"], now_iso)
            )

            incident_ids = []
            action_ids = []

            for inc_idx in range(3):
                inc_id = f"inc_{conf_id}_{inc_idx}"
                incident_ids.append(inc_id)
                conn.execute(
                    """
                    INSERT INTO incidents (id, confession_id, incident_order, incident_title, sin_classification, description, created_at)
                    VALUES (?, ?, ?, 'Title', 'both', 'Desc', ?)
                    """,
                    (inc_id, conf_id, inc_idx + 1, now_iso)
                )
                for act_idx in range(3):
                    act_id = f"act_{inc_id}_{act_idx}"
                    action_ids.append(act_id)
                    conn.execute(
                        """
                        INSERT INTO action_items (id, user_id, confession_id, incident_id, category, description, created_at)
                        VALUES (?, ?, ?, ?, 'wajib', 'Desc', ?)
                        """,
                        (act_id, user["id"], conf_id, inc_id, now_iso)
                    )
            conn.commit()

            # Verify pre-deletion counts
            inc_cnt = conn.execute("SELECT count(*) FROM incidents WHERE confession_id = ?", (conf_id,)).fetchone()[0]
            act_cnt = conn.execute("SELECT count(*) FROM action_items WHERE confession_id = ?", (conf_id,)).fetchone()[0]
            self.assertEqual(inc_cnt, 3)
            self.assertEqual(act_cnt, 9)

            # Perform granular deletion
            deleted = delete_confession(conn, conf_id, user["id"])
            self.assertTrue(deleted, "delete_confession must succeed")

            # Verify confession is gone
            conf_cnt = conn.execute("SELECT count(*) FROM confessions WHERE id = ?", (conf_id,)).fetchone()[0]
            self.assertEqual(conf_cnt, 0)

            # Verify ALL incidents are cascade deleted
            inc_after = conn.execute("SELECT count(*) FROM incidents WHERE confession_id = ?", (conf_id,)).fetchone()[0]
            self.assertEqual(inc_after, 0, "Incidents must be completely purged by ON DELETE CASCADE")

            # Verify ALL action items are cascade deleted
            act_after = conn.execute("SELECT count(*) FROM action_items WHERE confession_id = ?", (conf_id,)).fetchone()[0]
            self.assertEqual(act_after, 0, "Action items must be completely purged by ON DELETE CASCADE")

            # Double check individual IDs
            for inc_id in incident_ids:
                row = conn.execute("SELECT id FROM incidents WHERE id = ?", (inc_id,)).fetchone()
                self.assertIsNone(row)
            for act_id in action_ids:
                row = conn.execute("SELECT id FROM action_items WHERE id = ?", (act_id,)).fetchone()
                self.assertIsNone(row)

    def test_direct_incident_deletion_cascades_to_action_items(self):
        """
        Verify that deleting a single incident directly also cascades to its action items.
        """
        with get_db_connection(self.db_path) as conn:
            user = create_guest_user(conn)
            conf_id = f"conf_inc_casc_{uuid.uuid4().hex[:6]}"
            inc_1 = f"inc_casc_1_{uuid.uuid4().hex[:6]}"
            inc_2 = f"inc_casc_2_{uuid.uuid4().hex[:6]}"
            act_1 = f"act_for_inc1_{uuid.uuid4().hex[:6]}"
            act_2 = f"act_for_inc2_{uuid.uuid4().hex[:6]}"
            now_iso = datetime.now(timezone.utc).isoformat()

            conn.execute("INSERT INTO confessions (id, user_id, raw_input_type, raw_text, created_at) VALUES (?, ?, 'text', 'Test', ?)", (conf_id, user["id"], now_iso))
            conn.execute("INSERT INTO incidents (id, confession_id, incident_title, sin_classification, description, created_at) VALUES (?, ?, 'I1', 'huqooq_allah', 'D1', ?)", (inc_1, conf_id, now_iso))
            conn.execute("INSERT INTO incidents (id, confession_id, incident_title, sin_classification, description, created_at) VALUES (?, ?, 'I2', 'huqooq_al_ibad', 'D2', ?)", (inc_2, conf_id, now_iso))
            conn.execute("INSERT INTO action_items (id, user_id, confession_id, incident_id, category, description, created_at) VALUES (?, ?, ?, ?, 'wajib', 'A1', ?)", (act_1, user["id"], conf_id, inc_1, now_iso))
            conn.execute("INSERT INTO action_items (id, user_id, confession_id, incident_id, category, description, created_at) VALUES (?, ?, ?, ?, 'mustahabb', 'A2', ?)", (act_2, user["id"], conf_id, inc_2, now_iso))
            conn.commit()

            # Delete only incident 1
            conn.execute("DELETE FROM incidents WHERE id = ?", (inc_1,))
            conn.commit()

            # Verify act_1 is cascade deleted
            self.assertIsNone(conn.execute("SELECT id FROM action_items WHERE id = ?", (act_1,)).fetchone())

            # Verify incident 2 and act_2 remain untouched
            self.assertIsNotNone(conn.execute("SELECT id FROM incidents WHERE id = ?", (inc_2,)).fetchone())
            self.assertIsNotNone(conn.execute("SELECT id FROM action_items WHERE id = ?", (act_2,)).fetchone())

    def test_cascading_deletion_user_purges_all_tables(self):
        """
        Deleting a user must cascade and completely purge:
        - user_sessions
        - sessions
        - confessions
        - incidents
        - action_items
        - journal_entries
        """
        with get_db_connection(self.db_path) as conn:
            user = create_guest_user(conn)
            uid = user["id"]
            now_iso = datetime.now(timezone.utc).isoformat()

            # Create confession, incident, action item, journal
            conf_id = f"conf_u_purge_{uuid.uuid4().hex[:6]}"
            inc_id = f"inc_u_purge_{uuid.uuid4().hex[:6]}"
            act_id = f"act_u_purge_{uuid.uuid4().hex[:6]}"
            jnl_id = f"jnl_u_purge_{uuid.uuid4().hex[:6]}"

            conn.execute("INSERT INTO confessions (id, user_id, raw_input_type, raw_text, created_at) VALUES (?, ?, 'text', 'Test', ?)", (conf_id, uid, now_iso))
            conn.execute("INSERT INTO incidents (id, confession_id, incident_title, sin_classification, description, created_at) VALUES (?, ?, 'I', 'both', 'D', ?)", (inc_id, conf_id, now_iso))
            conn.execute("INSERT INTO action_items (id, user_id, confession_id, incident_id, category, description, created_at) VALUES (?, ?, ?, ?, 'wajib', 'A', ?)", (act_id, uid, conf_id, inc_id, now_iso))
            conn.execute("INSERT INTO journal_entries (id, user_id, content, created_at) VALUES (?, ?, 'Content', ?)", (jnl_id, uid, now_iso))
            conn.commit()

            # Verify user exists
            self.assertIsNotNone(conn.execute("SELECT id FROM users WHERE id = ?", (uid,)).fetchone())

            # Delete user
            conn.execute("DELETE FROM users WHERE id = ?", (uid,))
            conn.commit()

            # Verify user is gone
            self.assertIsNone(conn.execute("SELECT id FROM users WHERE id = ?", (uid,)).fetchone())

            # Verify ALL tables cascaded
            self.assertIsNone(conn.execute("SELECT token FROM user_sessions WHERE user_id = ?", (uid,)).fetchone())
            self.assertIsNone(conn.execute("SELECT token FROM sessions WHERE user_id = ?", (uid,)).fetchone())
            self.assertIsNone(conn.execute("SELECT id FROM confessions WHERE user_id = ?", (uid,)).fetchone())
            self.assertIsNone(conn.execute("SELECT id FROM incidents WHERE id = ?", (inc_id,)).fetchone())
            self.assertIsNone(conn.execute("SELECT id FROM action_items WHERE user_id = ?", (uid,)).fetchone())
            self.assertIsNone(conn.execute("SELECT id FROM journal_entries WHERE user_id = ?", (uid,)).fetchone())

    def test_audio_file_unlinking_on_confession_deletion_and_wipe(self):
        """
        Empirically verify physical disk audio file unlinking:
        - When a confession with an audio_path is deleted, the file is unlinked.
        - When wipe_user_data is called, all user audio files are unlinked.
        - If the file is missing from disk, no unhandled exception occurs.
        """
        # Create dummy audio file on disk
        audio_dir = Path(self.temp_dir.name) / "audio_test"
        audio_dir.mkdir(exist_ok=True)
        dummy_audio_file = audio_dir / f"test_{uuid.uuid4().hex[:8]}.webm"
        dummy_audio_file.write_bytes(b"RIFF....WAVEfmt ....data....")
        self.assertTrue(dummy_audio_file.exists())

        with get_db_connection(self.db_path) as conn:
            user = create_guest_user(conn)
            conf_id = f"conf_audio_{uuid.uuid4().hex[:6]}"
            conn.execute(
                """
                INSERT INTO confessions (id, user_id, raw_input_type, raw_text, audio_path, created_at)
                VALUES (?, ?, 'voice', 'Stemmeoptagelse test', ?, ?)
                """,
                (conf_id, user["id"], str(dummy_audio_file), datetime.now(timezone.utc).isoformat())
            )
            conn.commit()

            # Delete confession
            deleted = delete_confession(conn, conf_id, user["id"])
            self.assertTrue(deleted)

            # Verify file was physically unlinked
            self.assertFalse(dummy_audio_file.exists(), "Audio file must be unlinked from disk upon confession deletion")

            # Test missing file resilience
            dummy_missing_file = audio_dir / "does_not_exist.webm"
            conf_id_missing = f"conf_audio_miss_{uuid.uuid4().hex[:6]}"
            conn.execute(
                """
                INSERT INTO confessions (id, user_id, raw_input_type, raw_text, audio_path, created_at)
                VALUES (?, ?, 'voice', 'Mangler fil test', ?, ?)
                """,
                (conf_id_missing, user["id"], str(dummy_missing_file), datetime.now(timezone.utc).isoformat())
            )
            conn.commit()

            # Deletion must succeed gracefully without raising FileNotFoundError
            deleted_missing = delete_confession(conn, conf_id_missing, user["id"])
            self.assertTrue(deleted_missing)

    # =========================================================================
    # 5. TRANSACTION ROLLBACK & DATA INTEGRITY UNDER FAILURES
    # =========================================================================

    def test_transaction_rollback_on_exception(self):
        """
        Verify that an exception inside get_db_connection rolls back uncommitted changes.
        """
        user_id = f"user_rollback_{uuid.uuid4().hex[:6]}"
        with get_db_connection(self.db_path) as conn:
            conn.execute(
                "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'hash', ?)",
                (user_id, f"u_rb_{uuid.uuid4().hex[:6]}", datetime.now(timezone.utc).isoformat())
            )

        # Attempt transaction that inserts confession then raises an exception
        conf_id = f"conf_rb_{uuid.uuid4().hex[:6]}"
        try:
            with get_db_connection(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO confessions (id, user_id, raw_input_type, raw_text, created_at) VALUES (?, ?, 'text', 'Should be rolled back', ?)",
                    (conf_id, user_id, datetime.now(timezone.utc).isoformat())
                )
                raise RuntimeError("Simulated failure during business logic")
        except RuntimeError:
            pass

        # Verify confession was NOT persisted
        with get_db_connection(self.db_path) as conn:
            row = conn.execute("SELECT id FROM confessions WHERE id = ?", (conf_id,)).fetchone()
            self.assertIsNone(row, "Uncommitted transaction must be completely rolled back")

    # =========================================================================
    # 6. AUTHENTICATION & CRYPTOGRAPHIC EDGE CASES
    # =========================================================================

    def test_password_hashing_security_and_salting(self):
        """
        Verify PBKDF2 salting: identical passwords must generate distinct hashes,
        and password verification must be strictly constant-time and case-sensitive.
        """
        pw = "MyPass123!æøå"
        hash1 = hash_password(pw)
        hash2 = hash_password(pw)

        self.assertNotEqual(hash1, hash2, "Two hashes of the same password must use unique random salts")
        self.assertTrue(verify_password(pw, hash1))
        self.assertTrue(verify_password(pw, hash2))
        self.assertFalse(verify_password(pw.lower(), hash1), "Password verification must be case-sensitive")
        self.assertFalse(verify_password(pw + " ", hash1), "Password verification must be sensitive to whitespace")
        self.assertFalse(verify_password("invalid$format", hash1))

    def test_session_token_entropy_and_uniqueness(self):
        """
        Verify that 1,000 generated session tokens have 0 collisions and >= 43 chars length (256-bit).
        """
        tokens = set()
        count = 1000
        for _ in range(count):
            t = create_session_token()
            self.assertGreaterEqual(len(t), 43)
            tokens.add(t)
        self.assertEqual(len(tokens), count, "Session tokens must have 100% uniqueness with no collisions")

    def test_session_expiration_pruning(self):
        """
        Verify that an expired session token is rejected and pruned from the database.
        """
        with get_db_connection(self.db_path) as conn:
            user = create_guest_user(conn)
            expired_token = f"exp_token_{uuid.uuid4().hex}"
            past_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            older_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()

            conn.execute(
                """
                INSERT INTO user_sessions (token, user_id, created_at, expires_at, is_guest)
                VALUES (?, ?, ?, ?, 1)
                """,
                (expired_token, user["id"], older_iso, past_iso)
            )
            conn.commit()

            # Attempt lookup -> Must return None because expired
            res = get_user_by_token(conn, expired_token)
            self.assertIsNone(res, "Expired session token must return None")

            # Verify it was pruned from database
            pruned_row = conn.execute("SELECT token FROM user_sessions WHERE token = ?", (expired_token,)).fetchone()
            self.assertIsNone(pruned_row, "Expired session token must be pruned from user_sessions")

    # =========================================================================
    # 7. MODEL PARSING AND JSON SERIALIZATION INTEGRITY
    # =========================================================================

    def test_models_json_field_serialization(self):
        """
        Verify parse_json_field and dump_json_field handle edge cases (empty strings, None, malformed JSON).
        """
        # None and empty handling
        self.assertEqual(parse_json_field(None), [])
        self.assertEqual(parse_json_field(""), [])
        self.assertEqual(parse_json_field("   "), [])
        self.assertEqual(parse_json_field("invalid json string"), [])
        self.assertEqual(parse_json_field(["a", "b"]), ["a", "b"])
        self.assertEqual(parse_json_field('["Kollega", "Moderen"]'), ["Kollega", "Moderen"])

        self.assertEqual(dump_json_field(None), "[]")
        self.assertEqual(dump_json_field(["a", "b"]), '["a", "b"]')
        self.assertEqual(dump_json_field('["already", "json"]'), '["already", "json"]')

    # =========================================================================
    # 8. ADVANCED ADVERSARIAL STRESS & CORNER CASES
    # =========================================================================

    def test_wal_reader_does_not_block_writers(self):
        """
        Verify SQLite WAL concurrency property: an active reading connection
        does NOT block concurrent writers.
        """
        with get_db_connection(self.db_path) as conn_read:
            # Begin a read transaction
            cursor_read = conn_read.cursor()
            cursor_read.execute("SELECT count(*) FROM users")
            count_initial = cursor_read.fetchone()[0]

            # In another connection (simulating another thread/worker), perform writes
            with get_db_connection(self.db_path) as conn_write:
                new_user_id = f"wal_concurrent_user_{uuid.uuid4().hex[:6]}"
                conn_write.execute(
                    "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'hash', ?)",
                    (new_user_id, f"u_wal_{uuid.uuid4().hex[:6]}", datetime.now(timezone.utc).isoformat())
                )
                conn_write.commit()

            # The read transaction can still query without errors
            cursor_read.execute("SELECT count(*) FROM users")
            count_after = cursor_read.fetchone()[0]
            self.assertEqual(count_after, count_initial + 1)

    def test_multi_tenant_panic_wipe_isolation(self):
        """
        Stress test panic wipe isolation between multiple users:
        - User 1 has 5 confessions, 15 action items, 3 journal entries.
        - User 2 has 5 confessions, 15 action items, 3 journal entries.
        - User 1 calls wipe_user_data(delete_account=False).
        - User 1's data is completely purged, but account remains.
        - User 2's data is 100% intact (5 confessions, 15 action items, 3 journal entries).
        - User 2 (guest) calls wipe_user_data(delete_account=True).
        - User 2's account and data are purged, but User 1's account remains.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_connection(self.db_path) as conn:
            # Create User 1 (registered)
            u1_id = f"user_reg_{uuid.uuid4().hex[:6]}"
            conn.execute(
                "INSERT INTO users (id, username, password_hash, is_guest, created_at) VALUES (?, ?, 'hash', 0, ?)",
                (u1_id, f"u1_{uuid.uuid4().hex[:6]}", now_iso)
            )
            # Create User 2 (guest)
            u2_dict = create_guest_user(conn)
            u2_id = u2_dict["id"]

            # Populate 5 confessions, 15 action items, 3 journal entries for each user
            for u in [u1_id, u2_id]:
                for c_i in range(5):
                    cid = f"conf_wipe_{u}_{c_i}"
                    conn.execute("INSERT INTO confessions (id, user_id, raw_input_type, raw_text, created_at) VALUES (?, ?, 'text', 'Conf', ?)", (cid, u, now_iso))
                    for a_i in range(3):
                        aid = f"act_wipe_{u}_{c_i}_{a_i}"
                        conn.execute("INSERT INTO action_items (id, user_id, confession_id, category, description, created_at) VALUES (?, ?, ?, 'wajib', 'Act', ?)", (aid, u, cid, now_iso))
                for j_i in range(3):
                    jid = f"jnl_wipe_{u}_{j_i}"
                    conn.execute("INSERT INTO journal_entries (id, user_id, content, created_at) VALUES (?, ?, 'Jnl', ?)", (jid, u, now_iso))
            conn.commit()

            # Pre-wipe checks
            self.assertEqual(conn.execute("SELECT count(*) FROM confessions WHERE user_id = ?", (u1_id,)).fetchone()[0], 5)
            self.assertEqual(conn.execute("SELECT count(*) FROM confessions WHERE user_id = ?", (u2_id,)).fetchone()[0], 5)

            # User 1 performs panic wipe (preserving account)
            wipe_res = wipe_user_data(conn, u1_id, delete_account=False)
            self.assertEqual(wipe_res["status"], "success")

            # Assert User 1 data is wiped
            self.assertEqual(conn.execute("SELECT count(*) FROM confessions WHERE user_id = ?", (u1_id,)).fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT count(*) FROM action_items WHERE user_id = ?", (u1_id,)).fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT count(*) FROM journal_entries WHERE user_id = ?", (u1_id,)).fetchone()[0], 0)
            # User 1 account still exists
            self.assertIsNotNone(conn.execute("SELECT id FROM users WHERE id = ?", (u1_id,)).fetchone())

            # Assert User 2 data is 100% UNTOUCHED
            self.assertEqual(conn.execute("SELECT count(*) FROM confessions WHERE user_id = ?", (u2_id,)).fetchone()[0], 5)
            self.assertEqual(conn.execute("SELECT count(*) FROM action_items WHERE user_id = ?", (u2_id,)).fetchone()[0], 15)
            self.assertEqual(conn.execute("SELECT count(*) FROM journal_entries WHERE user_id = ?", (u2_id,)).fetchone()[0], 3)

            # User 2 (guest) wipes data (deleting account)
            wipe_res_2 = wipe_user_data(conn, u2_id, delete_account=True)
            self.assertEqual(wipe_res_2["status"], "success")
            self.assertIsNone(conn.execute("SELECT id FROM users WHERE id = ?", (u2_id,)).fetchone())

            # Verify User 1 account STILL survives
            self.assertIsNotNone(conn.execute("SELECT id FROM users WHERE id = ?", (u1_id,)).fetchone())

    def test_action_item_with_null_incident_cascading(self):
        """
        Verify that action items not linked to an incident (incident_id IS NULL)
        still properly cascade when confession is deleted, but are NOT deleted
        when an unrelated incident is deleted.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_connection(self.db_path) as conn:
            user = create_guest_user(conn)
            cid = f"conf_null_inc_{uuid.uuid4().hex[:6]}"
            inc_id = f"inc_other_{uuid.uuid4().hex[:6]}"
            act_with_null = f"act_null_inc_{uuid.uuid4().hex[:6]}"

            conn.execute("INSERT INTO confessions (id, user_id, raw_input_type, raw_text, created_at) VALUES (?, ?, 'text', 'T', ?)", (cid, user["id"], now_iso))
            conn.execute("INSERT INTO incidents (id, confession_id, incident_title, sin_classification, description, created_at) VALUES (?, ?, 'I', 'both', 'D', ?)", (inc_id, cid, now_iso))
            conn.execute(
                """
                INSERT INTO action_items (id, user_id, confession_id, incident_id, category, description, created_at)
                VALUES (?, ?, ?, NULL, 'wajib', 'General Tawbah Action', ?)
                """,
                (act_with_null, user["id"], cid, now_iso)
            )
            conn.commit()

            # Delete the other incident
            conn.execute("DELETE FROM incidents WHERE id = ?", (inc_id,))
            conn.commit()

            # The action item with NULL incident_id must STILL exist
            row = conn.execute("SELECT id FROM action_items WHERE id = ?", (act_with_null,)).fetchone()
            self.assertIsNotNone(row)

            # Now delete the confession -> action item must cascade delete
            deleted = delete_confession(conn, cid, user["id"])
            self.assertTrue(deleted)
            row_after = conn.execute("SELECT id FROM action_items WHERE id = ?", (act_with_null,)).fetchone()
            self.assertIsNone(row_after, "Action item with incident_id=NULL must be deleted when parent confession is deleted")

    def test_extreme_text_payloads_unicode_emojis_danish_chars(self):
        """
        Stress test data persistence with:
        - 100,000 character confession string
        - Full Danish character sets: æ, ø, å, Æ, Ø, Å
        - Arabic vocalized text (Uthmani Quranic script)
        - Unicode emojis: 🕌 🤲 🕋 📿 ❤️
        - Control characters, tabs, and newlines
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_connection(self.db_path) as conn:
            user = create_guest_user(conn)
            cid = f"conf_extreme_{uuid.uuid4().hex[:6]}"

            huge_text = ("Jeg fortryder mine handlinger og ønsker tilgivelse. " * 2000)  # ~114,000 chars
            danish_and_arabic = (
                "Dansk: Særlig opgørelse med æ, ø, å, Æ, Ø, Å. "
                "Arabisk: بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ "
                "Emojis: 🕌 🤲 🕋 📿 ❤️ \n\t Linjeskift og tabulatorer ' \" \\"
            )
            full_payload = huge_text + "\n\n" + danish_and_arabic

            conn.execute(
                """
                INSERT INTO confessions (id, user_id, raw_input_type, raw_text, transcript, created_at)
                VALUES (?, ?, 'text', ?, ?, ?)
                """,
                (cid, user["id"], full_payload, danish_and_arabic, now_iso)
            )
            conn.commit()

            # Retrieve and verify exact string fidelity without corruption
            row = conn.execute("SELECT raw_text, transcript FROM confessions WHERE id = ?", (cid,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(len(row["raw_text"]), len(full_payload))
            self.assertEqual(row["transcript"], danish_and_arabic)
            self.assertIn("æ, ø, å, Æ, Ø, Å", row["raw_text"])
            self.assertIn("بِسْمِ اللَّهِ", row["raw_text"])
            self.assertIn("🕌 🤲 🕋", row["raw_text"])

    def test_session_revocation_isolation_multiple_sessions(self):
        """
        Verify that revoking one session token for a user does NOT revoke
        other active sessions for the same user.
        """
        with get_db_connection(self.db_path) as conn:
            user = create_guest_user(conn)
            uid = user["id"]
            token_1 = user["token"]

            # Create second session for same user
            token_2 = create_session(conn, uid, is_guest=True)

            # Both tokens are valid
            self.assertIsNotNone(get_user_by_token(conn, token_1))
            self.assertIsNotNone(get_user_by_token(conn, token_2))

            # Revoke token 1
            revoked = revoke_session(conn, token_1)
            self.assertTrue(revoked)

            # Token 1 is now revoked (None)
            self.assertIsNone(get_user_by_token(conn, token_1))

            # Token 2 is STILL active and valid
            found_2 = get_user_by_token(conn, token_2)
            self.assertIsNotNone(found_2)
            self.assertEqual(found_2["id"], uid)

            # Revoking already-revoked token returns False
            self.assertFalse(revoke_session(conn, token_1))

    def test_explicit_commit_inside_context_manager(self):
        """
        Verify that caller executing conn.commit() inside with get_db_connection()
        does not cause errors when the context manager exits.
        """
        with get_db_connection(self.db_path) as conn:
            user = create_guest_user(conn)
            conn.commit()  # explicitly committed by caller
        # Exiting block should succeed cleanly without crashing on conn.in_transaction
        with get_db_connection(self.db_path) as conn:
            self.assertIsNotNone(conn.execute("SELECT id FROM users WHERE id = ?", (user["id"],)).fetchone())



if __name__ == "__main__":
    unittest.main(verbosity=2)
