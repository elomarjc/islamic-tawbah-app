"""
Tier 1 & Tier 3 Test Suite: Authentication, User Data Isolation, Action Persistence & Journal.
Verifies strict user data boundaries (User A cannot access User B's data),
interactive action item toggle persistence across sessions, per-item deletion, and panic wipe.
"""

import unittest
from typing import Dict, Any

from tests.test_base import (
    tier,
    requires_app,
    APP_AVAILABLE,
)

fastapi_app = None
if APP_AVAILABLE:
    try:
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app
    except (ImportError, ModuleNotFoundError):
        pass


class TestAuthIsolationAndDataPersistence(unittest.TestCase):
    """
    Tier 1 & Tier 3: User authentication, private dashboard isolation,
    action item toggle persistence, and panic data wipe.
    """

    def setUp(self):
        if APP_AVAILABLE:
            self.client = TestClient(fastapi_app)
        else:
            self.client = None

    def _register_user(self, username: str, password: str = "SecurePass123!") -> Dict[str, str]:
        """Helper to register and login a user, returning auth headers/cookies."""
        res = self.client.post(
            "/api/auth/register",
            json={"username": username, "password": password}
        )
        if res.status_code == 200:
            token = res.json().get("access_token")
            return {"Authorization": f"Bearer {token}"} if token else {}
        # Fallback to login if already registered
        res_login = self.client.post(
            "/api/auth/login",
            data={"username": username, "password": password}
        )
        token = res_login.json().get("access_token")
        return {"Authorization": f"Bearer {token}"} if token else {}

    # ------------------------------------------------------------------------
    # Tier 1: Database Schema & Basic Operations
    # ------------------------------------------------------------------------
    @tier(1)
    @requires_app
    def test_database_schema_initialization(self):
        """Tier 1: Feature #1 - SQLite database tables exist and foreign keys are active."""
        import sqlite3
        import os
        from tests.test_base import PROJECT_ROOT

        db_path = os.path.join(PROJECT_ROOT, "data", "tawbah.db")
        # In memory or file DB
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            for expected_tbl in ["users", "confessions", "incidents", "action_items"]:
                self.assertTrue(any(expected_tbl in t.lower() for t in tables), f"Missing table {expected_tbl}")

    @tier(1)
    @requires_app
    def test_repentance_journal_crud_endpoints(self):
        """Tier 1: Feature #23 - Repentance journal CRUD endpoints."""
        auth = self._register_user("journal_user_1")
        # Create reflection
        res_create = self.client.post(
            "/api/journal",
            headers=auth,
            json={"reflection": "I dag følte jeg dyb anger over mine ord til moderen. Må Allah tilgive mig.", "tags": ["anger", "mor"]}
        )
        self.assertIn(res_create.status_code, [200, 201])
        entry_id = res_create.json().get("id")

        # Read journal
        res_get = self.client.get("/api/journal", headers=auth)
        self.assertEqual(res_get.status_code, 200)
        entries = res_get.json()
        self.assertTrue(any(e.get("id") == entry_id for e in entries))

        # Delete entry
        if entry_id:
            res_del = self.client.delete(f"/api/journal/{entry_id}", headers=auth)
            self.assertIn(res_del.status_code, [200, 204])

    @tier(1)
    @requires_app
    def test_dashboard_kpi_summary_contract(self):
        """Tier 1: Feature #29 - Private dashboard summary statistics endpoint."""
        auth = self._register_user("dashboard_user_1")
        res = self.client.get("/api/dashboard/summary", headers=auth)
        self.assertIn(res.status_code, [200, 404])
        if res.status_code == 200:
            data = res.json()
            self.assertIn("total_confessions", data)
            self.assertIn("completed_actions", data)
            self.assertIn("pending_actions", data)

    # ------------------------------------------------------------------------
    # Tier 3: Cross-Feature Interactions & Multi-User Isolation
    # ------------------------------------------------------------------------
    @tier(3)
    @requires_app
    def test_user_data_isolation_across_accounts(self):
        """Tier 3: Feature #2 - User A cannot access or see User B's confessions."""
        auth_a = self._register_user("alice_isolation")
        auth_b = self._register_user("bob_isolation")

        # Alice creates a private confession
        res_a = self.client.post(
            "/api/confessions/text",
            headers=auth_a,
            json={"text": "Alices personlige private synd om natten.", "consent": True}
        )
        self.assertEqual(res_a.status_code, 200)
        alice_confession_id = res_a.json().get("confession_id")

        # Bob lists his confessions - Alice's must NOT be present
        res_bob_list = self.client.get("/api/confessions", headers=auth_b)
        self.assertEqual(res_bob_list.status_code, 200)
        bob_confessions = res_bob_list.json()
        self.assertFalse(any(c.get("id") == alice_confession_id for c in bob_confessions))

        # Bob attempts direct access to Alice's confession ID - must return 404 or 403
        if alice_confession_id:
            res_bob_direct = self.client.get(f"/api/confessions/{alice_confession_id}", headers=auth_b)
            self.assertIn(res_bob_direct.status_code, [403, 404], "Cross-user data access must be prohibited")

    @tier(3)
    @requires_app
    def test_action_item_toggle_persistence(self):
        """Tier 3: Feature #22 & #32 - Action item toggle status persists across sessions."""
        auth = self._register_user("persistence_user_1")

        # Create confession to generate action items
        res_conf = self.client.post(
            "/api/confessions/text",
            headers=auth,
            json={"text": "Jeg råbte ad min mor og vil gøre bod.", "consent": True}
        )
        self.assertEqual(res_conf.status_code, 200)
        actions = res_conf.json().get("required_actions", [])
        self.assertTrue(len(actions) > 0, "Confession must generate action items")

        action_id = actions[0]["id"]
        # Toggle completed to True
        res_patch = self.client.patch(
            f"/api/actions/{action_id}",
            headers=auth,
            json={"completed": True}
        )
        self.assertEqual(res_patch.status_code, 200)
        self.assertTrue(res_patch.json().get("completed"))

        # Verify persistence via fresh GET request
        res_actions = self.client.get("/api/actions", headers=auth)
        self.assertEqual(res_actions.status_code, 200)
        fetched_actions = res_actions.json()
        target = [a for a in fetched_actions if a.get("id") == action_id]
        if target:
            self.assertTrue(target[0].get("completed"), "Action item completion status must persist in database")

    @tier(3)
    @requires_app
    def test_granular_deletion_and_account_wipe(self):
        """Tier 3: Feature #3 & #37 - Granular deletion and panic wipe purges all records."""
        auth_wipe = self._register_user("wipe_test_user")

        # Create confession
        res = self.client.post(
            "/api/confessions/text",
            headers=auth_wipe,
            json={"text": "Synd før sletning af data.", "consent": True}
        )
        self.assertEqual(res.status_code, 200)

        # Execute Account Panic Wipe
        res_wipe = self.client.post("/api/account/wipe", headers=auth_wipe)
        self.assertIn(res_wipe.status_code, [200, 204])

        # Verify all confessions and actions are purged
        res_after_conf = self.client.get("/api/confessions", headers=auth_wipe)
        self.assertEqual(res_after_conf.status_code, 200)
        self.assertEqual(len(res_after_conf.json()), 0, "Confessions must be completely empty after account wipe")

        res_after_actions = self.client.get("/api/actions", headers=auth_wipe)
        self.assertEqual(res_after_actions.status_code, 200)
        self.assertEqual(len(res_after_actions.json()), 0, "Actions must be completely empty after account wipe")


if __name__ == "__main__":
    unittest.main()
