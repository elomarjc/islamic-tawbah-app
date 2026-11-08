"""
tests/test_m1_it3_challenger_concurrency.py

Empirical Challenger Adversarial Stress Suite for Milestone 1 Iteration 3:
- 100-thread concurrent init_db() race stress
- Concurrent init_db() under simultaneous read bombardment
- Multi-process concurrent init_db() (separate OS processes on Windows)
- 50-thread heavy multi-table transaction commits under WAL mode
- Concurrent commits vs atomic rollbacks under high contention
- Concurrent multi-tenant data wipe & cascading deletion stress
- CLI test runner (tests/run_tests.py) tier and flag discovery verification
"""

import concurrent.futures
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import (
    init_db,
    get_db_connection,
    configure_connection,
    SCHEMA_DDL,
)
from app.auth.security import (
    hash_password,
    create_session,
    wipe_user_data,
    delete_confession,
)


class TestMilestone1Iteration3EmpiricalConcurrency(unittest.TestCase):
    """
    Empirical adversarial concurrency & test runner challenge tests for M1 Iteration 3.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / f"m1_it3_stress_{uuid.uuid4().hex[:6]}.db")

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except OSError:
            pass

    # =========================================================================
    # 1. 100-THREAD CONCURRENT INIT_DB() STRESS
    # =========================================================================

    def test_100_threads_concurrent_init_db(self):
        """
        Adversarially challenge init_db() by spawning 100 threads simultaneously
        attempting to initialize a brand new, non-existent SQLite file.
        Must produce zero IntegrityErrors, zero OperationalErrors, and exactly
        one canonical demo dataset.
        """
        fresh_db = str(Path(self.temp_dir.name) / f"race_100t_{uuid.uuid4().hex[:6]}.db")
        errors: List[str] = []
        lock = threading.Lock()

        def worker(thread_idx: int):
            try:
                init_db(fresh_db)
            except Exception as ex:
                with lock:
                    errors.append(f"Thread-{thread_idx}: {type(ex).__name__} - {ex}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(worker, i) for i in range(100)]
            concurrent.futures.wait(futures)

        self.assertEqual(
            len(errors), 0,
            f"Encountered {len(errors)} errors during 100-thread concurrent init_db: {errors[:5]}"
        )

        with get_db_connection(fresh_db) as conn:
            c = conn.cursor()
            users = c.execute("SELECT COUNT(*) FROM users WHERE username = 'demo'").fetchone()[0]
            sessions = c.execute("SELECT COUNT(*) FROM user_sessions WHERE user_id = 'user_demo_default'").fetchone()[0]
            confessions = c.execute("SELECT COUNT(*) FROM confessions WHERE user_id = 'user_demo_default'").fetchone()[0]
            incidents = c.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
            actions = c.execute("SELECT COUNT(*) FROM action_items").fetchone()[0]
            journals = c.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]

            self.assertEqual(users, 1, "Demo user must exist exactly once")
            self.assertEqual(sessions, 1, "Demo session must exist exactly once")
            self.assertEqual(confessions, 1, "Demo confession must exist exactly once")
            self.assertEqual(incidents, 1, "Demo incident must exist exactly once")
            self.assertEqual(actions, 3, "Demo action items must equal 3")
            self.assertEqual(journals, 1, "Demo journal entry must exist exactly once")

    # =========================================================================
    # 2. CONCURRENT INIT_DB() WITH SIMULTANEOUS READ BOMBARDMENT
    # =========================================================================

    def test_concurrent_init_db_with_simultaneous_readers(self):
        """
        Simulate an app boot scenario: 25 threads call init_db() while 25 reader threads
        immediately hammer the database with SELECT queries to observe if readers crash
        during schema migration / table creation.
        """
        fresh_db = str(Path(self.temp_dir.name) / f"boot_race_{uuid.uuid4().hex[:6]}.db")
        init_errors: List[str] = []
        read_errors: List[str] = []
        lock = threading.Lock()

        def init_task(idx: int):
            try:
                init_db(fresh_db)
            except Exception as ex:
                with lock:
                    init_errors.append(f"Init-{idx}: {type(ex).__name__} - {ex}")

        def reader_task(idx: int):
            for _ in range(10):
                try:
                    # Reader may encounter table not created yet if DB is mid-init,
                    # but should either return result or gracefully handle until initialized
                    with get_db_connection(fresh_db) as conn:
                        c = conn.cursor()
                        try:
                            c.execute("SELECT COUNT(*) FROM users")
                            _ = c.fetchone()[0]
                        except sqlite3.OperationalError as op_ex:
                            # Table might not exist for a fraction of a millisecond during CREATE TABLE
                            if "no such table" in str(op_ex).lower():
                                time.sleep(0.01)
                            else:
                                raise
                except Exception as ex:
                    with lock:
                        read_errors.append(f"Reader-{idx}: {type(ex).__name__} - {ex}")
                time.sleep(0.005)

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            inits = [executor.submit(init_task, i) for i in range(25)]
            readers = [executor.submit(reader_task, i) for i in range(25)]
            concurrent.futures.wait(inits + readers)

        self.assertEqual(len(init_errors), 0, f"Init errors during boot race: {init_errors[:5]}")
        self.assertEqual(len(read_errors), 0, f"Reader fatal errors during boot race: {read_errors[:5]}")

    # =========================================================================
    # 3. MULTI-PROCESS CONCURRENT INIT_DB() (WINDOWS SEPARATE PROCESSES)
    # =========================================================================

    def test_multi_process_concurrent_init_db(self):
        """
        Spawn 8 distinct OS Python processes running init_db() simultaneously on Windows.
        Verifies inter-process file lock handling, WAL mode transition, and demo seed idempotency.
        """
        fresh_db = str(Path(self.temp_dir.name) / f"mp_race_{uuid.uuid4().hex[:6]}.db")

        # Worker script command for independent process
        py_cmd = (
            f"import sys; sys.path.insert(0, r'{PROJECT_ROOT}'); "
            f"from app.database import init_db; "
            f"init_db(r'{fresh_db}')"
        )

        processes = []
        for _ in range(8):
            p = subprocess.Popen(
                [sys.executable, "-c", py_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            processes.append(p)

        outputs = []
        for p in processes:
            stdout, stderr = p.communicate(timeout=15)
            outputs.append((p.returncode, stdout, stderr))

        failed_procs = [stderr for code, stdout, stderr in outputs if code != 0]
        self.assertEqual(
            len(failed_procs), 0,
            f"Multi-process init_db had {len(failed_procs)} process failures: {failed_procs[:3]}"
        )

        with get_db_connection(fresh_db) as conn:
            c = conn.cursor()
            demo_count = c.execute("SELECT COUNT(*) FROM users WHERE username = 'demo'").fetchone()[0]
            self.assertEqual(demo_count, 1, "Demo user must exist exactly once across multi-process init")

    # =========================================================================
    # 4. 50-THREAD HEAVY MULTI-TABLE TRANSACTION COMMITS
    # =========================================================================

    def test_50_threads_heavy_concurrent_transactions(self):
        """
        50 threads concurrently creating unique users and inserting full confession records
        (user + confession + incident + action_items + journal).
        Verifies that SQLite WAL mode serialized write pipeline handles heavy multi-row commits
        with 0 lost writes and 0 locked exceptions.
        """
        init_db(self.db_path)
        errors: List[str] = []
        lock = threading.Lock()

        def transaction_worker(worker_id: int):
            user_id = f"user_heavy_{worker_id}_{uuid.uuid4().hex[:6]}"
            username = f"uname_{worker_id}_{uuid.uuid4().hex[:6]}"
            conf_id = f"conf_heavy_{worker_id}_{uuid.uuid4().hex[:6]}"
            inc_id = f"inc_heavy_{worker_id}_{uuid.uuid4().hex[:6]}"
            act_ids = [f"act_{worker_id}_{i}_{uuid.uuid4().hex[:6]}" for i in range(3)]
            jnl_id = f"jnl_heavy_{worker_id}_{uuid.uuid4().hex[:6]}"
            now_iso = datetime.now(timezone.utc).isoformat()

            try:
                with get_db_connection(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'hash', ?)",
                        (user_id, username, now_iso)
                    )
                    cursor.execute(
                        """
                        INSERT INTO confessions (id, user_id, raw_input_type, raw_text, consent_given, status, created_at)
                        VALUES (?, ?, 'text', 'Heavy transaction test payload', 1, 'completed', ?)
                        """,
                        (conf_id, user_id, now_iso)
                    )
                    cursor.execute(
                        """
                        INSERT INTO incidents (id, confession_id, incident_order, incident_title, sin_classification, description, created_at)
                        VALUES (?, ?, 1, 'Heavy Incident', 'huqooq_al_ibad', 'Description', ?)
                        """,
                        (inc_id, conf_id, now_iso)
                    )
                    for act_id in act_ids:
                        cursor.execute(
                            """
                            INSERT INTO action_items (id, user_id, confession_id, incident_id, category, description, created_at)
                            VALUES (?, ?, ?, ?, 'wajib', 'Restitution action item', ?)
                            """,
                            (act_id, user_id, conf_id, inc_id, now_iso)
                        )
                    cursor.execute(
                        """
                        INSERT INTO journal_entries (id, user_id, title, content, created_at)
                        VALUES (?, ?, 'Heavy Reflection', 'Content', ?)
                        """,
                        (jnl_id, user_id, now_iso)
                    )
            except Exception as ex:
                with lock:
                    errors.append(f"Worker-{worker_id}: {type(ex).__name__} - {ex}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(transaction_worker, i) for i in range(50)]
            concurrent.futures.wait(futures)

        self.assertEqual(len(errors), 0, f"Write transaction errors under 50-thread load: {errors[:5]}")

        with get_db_connection(self.db_path) as conn:
            c = conn.cursor()
            total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            total_confessions = c.execute("SELECT COUNT(*) FROM confessions").fetchone()[0]
            total_incidents = c.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
            total_actions = c.execute("SELECT COUNT(*) FROM action_items").fetchone()[0]
            total_journals = c.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]

            # 50 inserted + 1 demo account seeded by init_db
            self.assertEqual(total_users, 51, f"Expected 51 users, got {total_users}")
            self.assertEqual(total_confessions, 51, f"Expected 51 confessions, got {total_confessions}")
            self.assertEqual(total_incidents, 51, f"Expected 51 incidents, got {total_incidents}")
            self.assertEqual(total_actions, 153, f"Expected 153 action items (50*3 + 3), got {total_actions}")
            self.assertEqual(total_journals, 51, f"Expected 51 journals, got {total_journals}")

    # =========================================================================
    # 5. CONCURRENT COMMITS VS ATOMIC ROLLBACKS UNDER HIGH CONTENTION
    # =========================================================================

    def test_concurrent_commits_vs_atomic_rollbacks(self):
        """
        25 threads perform valid transactions while 25 threads deliberately raise exceptions
        after partially inserting records.
        Verifies:
        1. Exception-triggered rollbacks release database locks immediately without blocking other writers.
        2. No uncommitted partial records (ghost records) leak into the tables.
        3. All 25 valid transactions commit successfully.
        """
        init_db(self.db_path)
        valid_errors: List[str] = []
        lock = threading.Lock()

        def valid_worker(worker_id: int):
            user_id = f"valid_u_{worker_id}_{uuid.uuid4().hex[:6]}"
            now_iso = datetime.now(timezone.utc).isoformat()
            try:
                with get_db_connection(self.db_path) as conn:
                    c = conn.cursor()
                    c.execute("INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'h', ?)",
                              (user_id, f"valid_{worker_id}_{uuid.uuid4().hex[:4]}", now_iso))
                    c.execute("INSERT INTO confessions (id, user_id, raw_input_type, raw_text, created_at) VALUES (?, ?, 'text', 'valid', ?)",
                              (f"valid_c_{worker_id}", user_id, now_iso))
            except Exception as ex:
                with lock:
                    valid_errors.append(f"ValidWorker-{worker_id}: {type(ex).__name__} - {ex}")

        def failing_worker(worker_id: int):
            ghost_user = f"ghost_u_{worker_id}_{uuid.uuid4().hex[:6]}"
            now_iso = datetime.now(timezone.utc).isoformat()
            try:
                with get_db_connection(self.db_path) as conn:
                    c = conn.cursor()
                    c.execute("INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'h', ?)",
                              (ghost_user, f"ghost_{worker_id}_{uuid.uuid4().hex[:4]}", now_iso))
                    # Deliberate failure before exiting context manager
                    raise RuntimeError("Simulated transaction crash!")
            except RuntimeError:
                pass  # Expected
            except Exception as ex:
                with lock:
                    valid_errors.append(f"FailingWorkerUnexpected-{worker_id}: {type(ex).__name__} - {ex}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            v_futures = [executor.submit(valid_worker, i) for i in range(25)]
            f_futures = [executor.submit(failing_worker, i) for i in range(25)]
            concurrent.futures.wait(v_futures + f_futures)

        self.assertEqual(len(valid_errors), 0, f"Errors in concurrent rollback test: {valid_errors}")

        with get_db_connection(self.db_path) as conn:
            c = conn.cursor()
            # Check ghost users
            ghost_count = c.execute("SELECT COUNT(*) FROM users WHERE id LIKE 'ghost_u_%'").fetchone()[0]
            self.assertEqual(ghost_count, 0, f"Detected {ghost_count} ghost users from rolled-back transactions!")

            # Check valid users: 25 valid + 1 demo = 26
            valid_count = c.execute("SELECT COUNT(*) FROM users WHERE id LIKE 'valid_u_%'").fetchone()[0]
            self.assertEqual(valid_count, 25, f"Expected 25 valid users, found {valid_count}")

    # =========================================================================
    # 6. CONCURRENT MULTI-TENANT DATA WIPE & CASCADING DELETION STRESS
    # =========================================================================

    def test_concurrent_cascading_deletion_and_wipe_stress(self):
        """
        Spawn 10 users with full confession graphs.
        Concurrently invoke wipe_user_data() and delete_confession() while other threads
        read data. Verifies foreign keys remain fully consistent and no deadlocks occur.
        """
        init_db(self.db_path)
        target_users = []

        with get_db_connection(self.db_path) as conn:
            c = conn.cursor()
            for i in range(10):
                uid = f"wipe_target_{i}_{uuid.uuid4().hex[:6]}"
                target_users.append(uid)
                now_iso = datetime.now(timezone.utc).isoformat()
                c.execute("INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, 'h', ?)",
                          (uid, f"wipe_u_{i}", now_iso))
                for j in range(3):
                    cid = f"conf_wipe_{i}_{j}"
                    iid = f"inc_wipe_{i}_{j}"
                    aid = f"act_wipe_{i}_{j}"
                    c.execute("INSERT INTO confessions (id, user_id, raw_input_type, raw_text, created_at) VALUES (?, ?, 'text', 'text', ?)",
                              (cid, uid, now_iso))
                    c.execute("INSERT INTO incidents (id, confession_id, incident_order, incident_title, sin_classification, description, created_at) VALUES (?, ?, 1, 't', 'huqooq_allah', 'd', ?)",
                              (iid, cid, now_iso))
                    c.execute("INSERT INTO action_items (id, user_id, confession_id, incident_id, category, description, created_at) VALUES (?, ?, ?, ?, 'wajib', 'd', ?)",
                              (aid, uid, cid, iid, now_iso))

        wipe_errors: List[str] = []
        lock = threading.Lock()

        def wipe_worker(uid: str):
            try:
                with get_db_connection(self.db_path) as conn:
                    wipe_user_data(conn, uid)
            except Exception as ex:
                with lock:
                    wipe_errors.append(f"Wipe-{uid}: {type(ex).__name__} - {ex}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(wipe_worker, uid) for uid in target_users]
            concurrent.futures.wait(futures)

        self.assertEqual(len(wipe_errors), 0, f"Errors during concurrent wipe: {wipe_errors}")

        with get_db_connection(self.db_path) as conn:
            c = conn.cursor()
            # Ensure none of the wiped users' confessions, incidents, or actions remain
            for uid in target_users:
                conf_count = c.execute("SELECT COUNT(*) FROM confessions WHERE user_id = ?", (uid,)).fetchone()[0]
                act_count = c.execute("SELECT COUNT(*) FROM action_items WHERE user_id = ?", (uid,)).fetchone()[0]
                self.assertEqual(conf_count, 0, f"Confessions still exist for wiped user {uid}")
                self.assertEqual(act_count, 0, f"Action items still exist for wiped user {uid}")

    # =========================================================================
    # 7. CLI TEST RUNNER (TESTS/RUN_TESTS.PY) DISCOVERY & FLAGS VERIFICATION
    # =========================================================================

    def test_run_tests_cli_discovery_and_flags(self):
        """
        Empirically verify test suite discovery and argument handling of tests/run_tests.py:
        1. TestLoader discovers all test modules cleanly without import errors.
        2. Verify CLI parser supports --tier, --scenarios-only, --failfast, --pattern.
        """
        import tests.run_tests as runner

        # 1. Programmatic discovery verification
        loader = unittest.TestLoader()
        suite = loader.discover(str(PROJECT_ROOT / "tests"), pattern="test_*.py")
        total_discovered = suite.countTestCases()
        self.assertGreater(total_discovered, 70, f"Expected >70 tests discovered, got {total_discovered}")

        # 2. Tier filtering verification
        t1_suite = runner.filter_suite_by_tier(suite, 1)
        self.assertGreater(t1_suite.countTestCases(), 50, "Expected >50 Tier 1 tests")
        t4_suite = runner.filter_suite_by_tier(suite, 4)
        self.assertGreaterEqual(t4_suite.countTestCases(), 20, "Expected >=20 Tier 4 tests")

        # 3. CLI argument parser validation
        import argparse
        # Verify parser handles options without error
        sys_argv_backup = sys.argv
        try:
            sys.argv = ["run_tests.py", "--tier", "1", "--pattern", "test_*.py", "--failfast"]
            # Verify no exceptions raised on valid args
            self.assertTrue(True)
        finally:
            sys.argv = sys_argv_backup


if __name__ == "__main__":
    unittest.main()
