"""
tests/test_m1_it2_concurrency_stress.py

Empirical Challenger Adversarial Stress Suite for Milestone 1 Iteration 2:
- Heavy SQLite WAL Concurrency Stress (50 concurrent threads, 500+ mixed ops)
- Concurrent init_db() race condition resilience
- Mixed Commits and Intentional Rollbacks under high concurrency
- Windows File Handle & Rapid Connection Churn Stress
- Adversarial Unicode (Bidi overrides, RTL markers, Zalgo, null bytes) in RAG anti-hallucination
- ActionItemSchema and ActionItem Model bidirectional roundtrip & edge case stress
- Multi-Tenant Panic Wipe Concurrency Race
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
from datetime import datetime, timezone
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
from app.schemas import ActionItemSchema
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
from app.engine.rag_service import (
    IslamicRAGService,
    get_rag_service,
    verify_citation,
    normalize_text,
    normalize_arabic,
)


class TestMilestone1Iteration2EmpiricalStress(unittest.TestCase):
    """
    Adversarial empirical stress tests written by Challenger M1 Iteration 2.
    """

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = str(Path(cls.temp_dir.name) / "m1_it2_stress.db")
        init_db(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.temp_dir.cleanup()
        except OSError:
            pass

    # =========================================================================
    # 1. HEAVY SQLITE WAL CONCURRENCY (50 THREADS, 500+ MIXED OPS)
    # =========================================================================

    def test_50_threads_high_concurrency_wal(self):
        """
        Stress test SQLite WAL with 50 concurrent threads:
        - 25 writer threads executing 10 transactions each (250 writes total)
        - 25 reader threads continuously querying users and confessions
        Must achieve 100% success rate with ZERO 'database is locked' errors.
        """
        write_errors: List[str] = []
        read_errors: List[str] = []
        writes_completed = [0]
        lock = threading.Lock()

        # Seed 5 target users for writers
        users = [f"stress_user_{i}_{uuid.uuid4().hex[:6]}" for i in range(5)]
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            for u in users:
                cursor.execute(
                    "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'hash', ?)",
                    (u, u, datetime.now(timezone.utc).isoformat())
                )

        def writer_task(thread_id: int):
            user_id = users[thread_id % len(users)]
            for op in range(10):
                conf_id = f"conf_50t_{thread_id}_{op}_{uuid.uuid4().hex[:6]}"
                inc_id = f"inc_50t_{thread_id}_{op}_{uuid.uuid4().hex[:6]}"
                act_id = f"act_50t_{thread_id}_{op}_{uuid.uuid4().hex[:6]}"
                now_iso = datetime.now(timezone.utc).isoformat()
                try:
                    with get_db_connection(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO confessions (id, user_id, raw_input_type, raw_text, consent_given, status, created_at)
                            VALUES (?, ?, 'text', 'Adversarial 50-thread stress text payload', 1, 'completed', ?)
                            """,
                            (conf_id, user_id, now_iso)
                        )
                        cursor.execute(
                            """
                            INSERT INTO incidents (id, confession_id, incident_order, incident_title, sin_classification, description, created_at)
                            VALUES (?, ?, 1, 'Stress Incident', 'huqooq_allah', 'Description', ?)
                            """,
                            (inc_id, conf_id, now_iso)
                        )
                        cursor.execute(
                            """
                            INSERT INTO action_items (id, user_id, confession_id, incident_id, category, description, created_at)
                            VALUES (?, ?, ?, ?, 'wajib', 'Action Item Description', ?)
                            """,
                            (act_id, user_id, conf_id, inc_id, now_iso)
                        )
                    with lock:
                        writes_completed[0] += 1
                except Exception as ex:
                    with lock:
                        write_errors.append(f"Writer-{thread_id}-{op}: {type(ex).__name__} - {ex}")

        def reader_task(thread_id: int):
            for _ in range(15):
                try:
                    with get_db_connection(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM confessions")
                        _ = cursor.fetchone()[0]
                        cursor.execute("SELECT COUNT(*) FROM action_items")
                        _ = cursor.fetchone()[0]
                except Exception as ex:
                    with lock:
                        read_errors.append(f"Reader-{thread_id}: {type(ex).__name__} - {ex}")
                time.sleep(0.005)

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            writer_futures = [executor.submit(writer_task, i) for i in range(25)]
            reader_futures = [executor.submit(reader_task, i) for i in range(25)]
            concurrent.futures.wait(writer_futures + reader_futures)

        self.assertEqual(len(write_errors), 0, f"Write errors encountered under 50-thread load: {write_errors[:5]}")
        self.assertEqual(len(read_errors), 0, f"Read errors encountered under 50-thread load: {read_errors[:5]}")
        self.assertEqual(writes_completed[0], 250, "Expected 250 write transactions completed")

    # =========================================================================
    # 2. CONCURRENT INIT_DB() RACE RESILIENCE
    # =========================================================================

    def test_concurrent_init_db_race_condition(self):
        """
        10 threads simultaneously calling init_db() on a newly created SQLite file.
        Measures whether concurrent init_db() without INSERT OR IGNORE causes UNIQUE constraint IntegrityErrors.
        """
        fresh_db = str(Path(self.temp_dir.name) / f"race_init_{uuid.uuid4().hex[:6]}.db")
        integrity_errors: List[str] = []

        def init_task(idx: int):
            try:
                init_db(fresh_db)
            except sqlite3.IntegrityError as ex:
                integrity_errors.append(f"Thread-{idx}: {ex}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(init_task, i) for i in range(10)]
            concurrent.futures.wait(futures)

        # Verified remediation: with INSERT OR IGNORE and safe transaction guards,
        # zero IntegrityErrors occur under concurrent init_db calls.
        self.assertEqual(len(integrity_errors), 0, f"Integrity errors during concurrent init_db: {integrity_errors}")
        with get_db_connection(fresh_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'demo'")
            count = cursor.fetchone()[0]
            self.assertEqual(count, 1, "Demo user must exist exactly once")

    # =========================================================================
    # 3. MIXED COMMITS AND INTENTIONAL ROLLBACKS UNDER CONCURRENCY
    # =========================================================================

    def test_mixed_commits_and_rollbacks_concurrency(self):
        """
        20 concurrent workers:
        - 10 workers execute valid commits
        - 10 workers intentionally raise exceptions inside the context manager
        Verify that rollbacks leave zero orphaned rows and valid commits are preserved.
        """
        user_id = f"user_rollback_test_{uuid.uuid4().hex[:6]}"
        with get_db_connection(self.db_path) as conn:
            conn.cursor().execute(
                "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'hash', ?)",
                (user_id, user_id, datetime.now(timezone.utc).isoformat())
            )

        def worker(thread_id: int):
            now_iso = datetime.now(timezone.utc).isoformat()
            if thread_id % 2 == 0:
                # Valid transaction
                with get_db_connection(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO journal_entries (id, user_id, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
                        (f"jnl_valid_{thread_id}", user_id, f"Valid {thread_id}", "Content", now_iso)
                    )
            else:
                # Transaction that aborts midway
                try:
                    with get_db_connection(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO journal_entries (id, user_id, title, content, created_at) VALUES (?, ?, ?, ?, ?)",
                            (f"jnl_abort_{thread_id}", user_id, f"Aborted {thread_id}", "Content", now_iso)
                        )
                        raise RuntimeError("Simulated failure to trigger rollback")
                except RuntimeError:
                    pass

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            concurrent.futures.wait(futures)

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM journal_entries WHERE user_id = ?", (user_id,))
            saved_ids = [row[0] for row in cursor.fetchall()]

        self.assertEqual(len(saved_ids), 10, f"Expected exactly 10 committed entries, found {len(saved_ids)}")
        for i in range(20):
            if i % 2 == 0:
                self.assertIn(f"jnl_valid_{i}", saved_ids)
            else:
                self.assertNotIn(f"jnl_abort_{i}", saved_ids)

    # =========================================================================
    # 4. WINDOWS FILE HANDLE & RAPID CONNECTION CHURN
    # =========================================================================

    def test_connection_rapid_churn_stress(self):
        """
        Test rapid open/close of 100 SQLite connections across 10 threads.
        Ensures no file handle leaks or 'unable to open database file' on Windows.
        """
        errors = []

        def churn_worker(thread_id: int):
            for i in range(10):
                try:
                    with get_db_connection(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT 1;")
                        val = cursor.fetchone()[0]
                        assert val == 1
                except Exception as ex:
                    errors.append(f"Churn-{thread_id}-{i}: {ex}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(churn_worker, i) for i in range(10)]
            concurrent.futures.wait(futures)

        self.assertEqual(len(errors), 0, f"Rapid connection churn errors: {errors}")

    # =========================================================================
    # 5. ADVERSARIAL UNICODE & BIDI ATTACKS ON RAG ANTI-HALLUCINATION
    # =========================================================================

    def test_adversarial_unicode_and_types_in_rag_service(self):
        """
        Pass adversarial payloads into RAG service:
        - Bidi overrides (\u202e), RTL markers, null bytes, Zalgo text
        - Non-string types (None, dict, list, float, int)
        - Massive strings (50,000 chars)
        Verify no unhandled exceptions and no anti-hallucination filter bypasses.
        """
        rag = get_rag_service()

        # 1. Non-string types and invalid source types
        self.assertFalse(verify_citation(None, None, None))
        self.assertFalse(verify_citation("invalid_source", "Bukhari", 2449))
        self.assertFalse(verify_citation("Hadith", "", 2449))
        self.assertFalse(verify_citation("Hadith", "sahih", 2449))
        self.assertFalse(rag.verify_quran_citation(None, None))
        self.assertFalse(rag.verify_hadith_citation(None, None))
        self.assertFalse(rag.verify_dua(None))
        self.assertFalse(rag.verify_dua({"title": None, "arabic_text": None}))

        # 2. Fake collection and fake hadith number
        self.assertFalse(rag.verify_hadith_citation("FakeCollection", "2449"))
        self.assertFalse(rag.verify_hadith_citation("Fabricated_Sunnah", "1"))
        evil_collection = "Bukhari\u202e\u202d\x00_fake"
        self.assertFalse(rag.verify_hadith_citation(evil_collection, "99999"))

        # 3. Zalgo text with fake number
        zalgo = "B̷u̵k̸h̸a̸r̴i̶"
        self.assertFalse(rag.verify_hadith_citation(zalgo, "99999"))

        # 4. Enormous query string search resilience
        huge_query = "استغفار " * 5000  # ~45,000 characters
        results = rag.search_quran(huge_query)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

        results_hadith = rag.search_hadith(huge_query)
        self.assertIsInstance(results_hadith, list)

        results_duas = rag.search_duas(huge_query)
        self.assertIsInstance(results_duas, list)

        # 5. Sanitizer with poisoned analysis dictionary containing valid dict shapes
        poisoned_analysis = {
            "quran_references": [
                {"surah": "Az-Zumar", "ayah": 53, "arabic_text": "text", "danish_translation": "da", "explanation": "exp"},
                {"surah": "FakeSurah\x00", "ayah": 9999, "arabic_text": "evil", "danish_translation": "evil", "explanation": "evil"},
            ],
            "hadith_references": [
                {"collection": "Sahih al-Bukhari", "hadith_number": "2449", "authenticity_grading": "Sahih", "danish_translation": "da", "explanation": "exp"},
                {"collection": "sahih", "hadith_number": "2449", "authenticity_grading": "Sahih", "danish_translation": "da", "explanation": "exp"},
            ],
            "recommended_duas": [
                {"title": "Sayyid al-Istighfar", "arabic_text": "اللَّهُمَّ أَنْتَ رَبِّي", "transliteration": "t", "danish_translation": "d", "source": "s", "context": "c"},
                {"title": "Fabricated\u202eDua", "arabic_text": "بِسْمِ شَيْطَان", "transliteration": "t", "danish_translation": "d", "source": "s", "context": "c"}
            ]
        }
        sanitized = rag.validate_and_sanitize_analysis(poisoned_analysis)
        # Verify invalid citations were pruned
        q_surahs = [q["surah"] for q in sanitized["quran_references"]]
        self.assertEqual(q_surahs, ["Az-Zumar"])

        h_colls = [h["collection"] for h in sanitized["hadith_references"]]
        self.assertEqual(h_colls, ["Sahih al-Bukhari"])

        d_titles = [d["title"] for d in sanitized["recommended_duas"]]
        self.assertIn("Sayyid al-Istighfar", d_titles[0])
        self.assertEqual(len(sanitized["recommended_duas"]), 1)

        # 6. Empirical Verification: NoneType list element is handled gracefully without crash
        sanitized_none = rag.validate_and_sanitize_analysis({"quran_references": [None]})
        self.assertGreaterEqual(len(sanitized_none["quran_references"]), 1)

    # =========================================================================
    # 6. ACTION ITEM SCHEMA & MODEL BIDIRECTIONAL ROUNDTRIP STRESS
    # =========================================================================

    def test_action_item_schema_and_model_roundtrip_edge_cases(self):
        """
        Stress test ActionItemSchema and ActionItem model:
        - All 10 legal & granular categories
        - Schema -> Model -> Row Dict -> Model -> Schema roundtrip
        - Danish characters, long explanations, optional fields
        """
        all_categories = [
            ("wajib", "tawbah_allah", "wajib"),
            ("mustahabb", "dua", "mustahabb"),
            ("tawbah_allah", "tawbah_allah", "wajib"),
            ("restitution", "restitution", "wajib"),
            ("rectification", "rectification", "wajib"),
            ("apology", "apology", "wajib"),
            ("sadaqah", "sadaqah", "mustahabb"),
            ("dua", "dua", "mustahabb"),
            ("extra_prayers", "extra_prayers", "mustahabb"),
            ("self_discipline", "self_discipline", "mustahabb"),
        ]

        user_id = f"user_ai_{uuid.uuid4().hex[:6]}"
        conf_id = f"conf_ai_{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'hash', ?)",
                (user_id, user_id, now_iso)
            )
            cursor.execute(
                "INSERT INTO confessions (id, user_id, raw_input_type, raw_text, consent_given, status, created_at) VALUES (?, ?, 'text', 'test', 1, 'completed', ?)",
                (conf_id, user_id, now_iso)
            )

        for cat_input, expected_granular, expected_legal in all_categories:
            schema_in = ActionItemSchema(
                id=f"act_{uuid.uuid4().hex[:8]}",
                category=cat_input,
                title=f"Handling for {cat_input} (æøå)",
                description="Udfør handling på dansk med æ, ø, å og Æ, Ø, Å",
                explanation="Lang forklaring med fiqh-begrundelse.",
                target_party="Offer / Modpart",
                completed=False
            )
            self.assertEqual(schema_in.legal_category, expected_legal)
            self.assertEqual(schema_in.granular_type, expected_granular)

            # Convert to model
            model_obj = ActionItem.from_schema(schema_in, user_id=user_id, confession_id=conf_id)
            self.assertEqual(model_obj.category, expected_legal)
            self.assertEqual(model_obj.action_type, expected_granular)

            # Persist to database
            with get_db_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO action_items (id, user_id, confession_id, category, action_type, title, description, explanation, target_party, completed, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (model_obj.id, model_obj.user_id, model_obj.confession_id, model_obj.category, model_obj.action_type,
                     model_obj.title, model_obj.description, model_obj.explanation, model_obj.target_party,
                     1 if model_obj.completed else 0, model_obj.created_at)
                )

                # Fetch row back
                cursor.execute("SELECT * FROM action_items WHERE id = ?", (model_obj.id,))
                row = dict(cursor.fetchone())

            # Convert row back to model
            model_from_row = ActionItem.from_row(row)
            self.assertEqual(model_from_row.category, expected_legal)
            self.assertEqual(model_from_row.action_type, expected_granular)

            # Convert back to schema dict
            schema_dict = model_from_row.to_schema_dict()
            schema_out = ActionItemSchema(**schema_dict)
            self.assertEqual(schema_out.id, schema_in.id)
            self.assertEqual(schema_out.legal_category, expected_legal)
            self.assertEqual(schema_out.description, schema_in.description)

    # =========================================================================
    # 7. MULTI-TENANT PANIC WIPE CONCURRENCY RACE
    # =========================================================================

    def test_panic_wipe_concurrency_race(self):
        """
        User A is actively inserting confessions and journals while User B
        triggers wipe_user_data(user_b).
        Verify:
        - User B's wipe succeeds completely
        - User A's concurrent inserts are NOT affected or wiped
        - Zero foreign key or lock exceptions
        """
        user_a = f"user_wipe_a_{uuid.uuid4().hex[:6]}"
        user_b = f"user_wipe_b_{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'hash', ?)", (user_a, user_a, now_iso))
            cursor.execute("INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'hash', ?)", (user_b, user_b, now_iso))

        # Seed User B with 10 confessions
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            for i in range(10):
                c_id = f"conf_b_{i}_{uuid.uuid4().hex[:6]}"
                cursor.execute(
                    "INSERT INTO confessions (id, user_id, raw_input_type, raw_text, consent_given, status, created_at) VALUES (?, ?, 'text', 'B data', 1, 'completed', ?)",
                    (c_id, user_b, now_iso)
                )

        race_errors = []
        user_a_inserted = [0]
        lock = threading.Lock()

        def user_a_work():
            for i in range(15):
                c_id = f"conf_a_{i}_{uuid.uuid4().hex[:6]}"
                try:
                    with get_db_connection(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO confessions (id, user_id, raw_input_type, raw_text, consent_given, status, created_at) VALUES (?, ?, 'text', 'A data', 1, 'completed', ?)",
                            (c_id, user_a, datetime.now(timezone.utc).isoformat())
                        )
                    with lock:
                        user_a_inserted[0] += 1
                except Exception as ex:
                    with lock:
                        race_errors.append(f"UserA-Insert: {ex}")
                time.sleep(0.005)

        def user_b_wipe():
            time.sleep(0.02)  # Wait for User A work to be in-flight
            try:
                with get_db_connection(self.db_path) as conn:
                    wipe_user_data(conn, user_b)
            except Exception as ex:
                with lock:
                    race_errors.append(f"UserB-Wipe: {ex}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            fut_a = executor.submit(user_a_work)
            fut_b = executor.submit(user_b_wipe)
            concurrent.futures.wait([fut_a, fut_b])

        self.assertEqual(len(race_errors), 0, f"Race errors during panic wipe: {race_errors}")
        self.assertEqual(user_a_inserted[0], 15, "User A must have 15 inserted confessions")

        # Verify User B has 0 confessions, User A has exactly 15
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM confessions WHERE user_id = ?", (user_b,))
            self.assertEqual(cursor.fetchone()[0], 0, "User B's confessions must be 0 after wipe")
            cursor.execute("SELECT COUNT(*) FROM confessions WHERE user_id = ?", (user_a,))
            self.assertEqual(cursor.fetchone()[0], 15, "User A's confessions must remain 15")


if __name__ == "__main__":
    unittest.main()
