"""
Tier 1, Tier 2 & Tier 3 Test Suite: Rights Classification, Fiqh Rules & Multi-Sin Splitting.
Verifies pure Huqooq Allah vs Huqooq al-Ibad vs Both classification, the 4 conditions of Tawbah,
incident splitting, fitnah avoidance, Sitr concealment, and anonymous restitution.
"""

import unittest
from typing import Dict, Any

from tests.test_base import (
    tier,
    requires_app,
    APP_AVAILABLE,
    ReferenceIncidentSchema,
    ReferenceActionItemSchema,
)

fastapi_app = None
if APP_AVAILABLE:
    try:
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app
    except (ImportError, ModuleNotFoundError):
        pass


class TestRightsClassificationAndFiqhRules(unittest.TestCase):
    """
    Tier 1, 2 & 3: Rights classification taxonomy, conditions of Tawbah,
    incident splitting, and nuanced fiqh rules.
    """

    def setUp(self):
        if APP_AVAILABLE:
            self.client = TestClient(fastapi_app)
        else:
            self.client = None

    # ------------------------------------------------------------------------
    # Tier 1: Rights Classification Taxonomy & Tawbah Conditions
    # ------------------------------------------------------------------------
    @tier(1)
    def test_rights_classification_contract_taxonomy(self):
        """Tier 1: Feature #9 - Verify taxonomy allows only huqooq_allah, huqooq_al_ibad, both."""
        valid_classes = ["huqooq_allah", "huqooq_al_ibad", "both"]
        for cls_name in valid_classes:
            inc = ReferenceIncidentSchema(
                incident_id="inc-test",
                description="Test beskrivelse",
                sin_classification=cls_name,
                affected_parties=["Part"] if cls_name != "huqooq_allah" else [],
            )
            self.assertEqual(inc.sin_classification, cls_name)

    @tier(1)
    @requires_app
    def test_rights_classification_pure_allah(self):
        """Tier 1: Feature #9 - Pure Huqooq Allah classifications (Prayer, Fasting, Secret Sins)."""
        # Missed prayer
        res_prayer = self.client.post(
            "/api/confessions/text",
            json={"text": "Jeg sov over mig og missede Asr-bønnen med vilje i dag.", "consent": True}
        )
        self.assertEqual(res_prayer.status_code, 200)
        self.assertEqual(res_prayer.json()["sin_classification"], "huqooq_allah")
        self.assertEqual(len(res_prayer.json()["affected_parties"]), 0)

        # Breaking voluntary fast
        res_fast = self.client.post(
            "/api/confessions/text",
            json={"text": "Jeg brød min faste i Ramadan med vilje uden gyldig grund.", "consent": True}
        )
        self.assertEqual(res_fast.status_code, 200)
        self.assertEqual(res_fast.json()["sin_classification"], "huqooq_allah")

    @tier(1)
    @requires_app
    def test_rights_classification_both_rights(self):
        """Tier 1: Feature #9 - Sins violating both Allah's boundaries and human rights."""
        # Fraudulent financial theft
        res_theft = self.client.post(
            "/api/confessions/text",
            json={"text": "Jeg snød min forretningspartner for 10.000 kr i vores fælles regnskab.", "consent": True}
        )
        self.assertEqual(res_theft.status_code, 200)
        self.assertEqual(res_theft.json()["sin_classification"], "both")
        self.assertTrue(len(res_theft.json()["affected_parties"]) >= 1)

    @tier(1)
    @requires_app
    def test_core_tawbah_conditions_presence(self):
        """Tier 1: Feature #10 - Core conditions of Tawbah (Remorse, Cessation, Resolve)."""
        res = self.client.post(
            "/api/confessions/text",
            json={"text": "Jeg begik en synd og vil gerne vende om til Allah.", "consent": True}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        req_actions = data["required_actions"]
        descriptions = " ".join([a["description"].lower() + " " + a.get("explanation", "").lower()
                                for a in req_actions])

        # Remorse (Nadam)
        self.assertTrue(any(w in descriptions for w in ["anger", "fortrydelse", "nadam"]))
        # Cessation (Iqla')
        self.assertTrue(any(w in descriptions for w in ["ophør", "stop", "afstå", "iqla"]))
        # Resolve never to return (Azm)
        self.assertTrue(any(w in descriptions for w in ["beslutning", "gentage", "aldrig mere", "azm"]))

    @tier(1)
    @requires_app
    def test_restitution_engine_for_property_rights(self):
        """Tier 1: Feature #11 - Property usurpation mandates 4th condition (Radd al-Mazalim)."""
        res = self.client.post(
            "/api/confessions/text",
            json={"text": "Jeg stjal min vens cykel og solgte den på nettet for 1500 kr.", "consent": True}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["sin_classification"], "both")
        restitution_guidance = (data.get("restitution_guidance") or "").lower()
        self.assertTrue(any(w in restitution_guidance for w in ["erstatning", "tilbage", "kompensation", "værdi", "penge"]))

    @tier(1)
    @requires_app
    def test_scholarly_disagreement_disclosure(self):
        """Tier 1: Feature #15 - Transparent disclosure of scholarly difference of opinion (Ikhtilaf)."""
        # Backbiting where victim is unaware has classical ikhtilaf
        res = self.client.post(
            "/api/confessions/text",
            json={"text": "Jeg bagtalte min ven foran andre, men han aner det ikke.", "consent": True}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        # Must contain explanation of scholarly views (Jumhur vs Ibn Taymiyyah/Ibn Qayyim)
        disagreement = (data.get("scholarly_disagreement") or "").lower()
        self.assertTrue(len(disagreement) > 10, "Scholarly disagreement must be documented for backbiting")

    @tier(1)
    @requires_app
    def test_scholar_consultation_flag_trigger(self):
        """Tier 1: Feature #16 - Flag triggered for physical harm, domestic abuse, or severe crimes."""
        res_violence = self.client.post(
            "/api/confessions/text",
            json={"text": "Jeg udøvede fysisk vold mod min ægtefælle og slog hende gentagne gange.", "consent": True}
        )
        self.assertEqual(res_violence.status_code, 200)
        data = res_violence.json()
        self.assertTrue(data.get("scholar_consultation_required"), "Severe harm must require scholar consultation")

    @tier(1)
    @requires_app
    def test_restitution_and_apology_drawer_content(self):
        """Tier 1: Feature #33 - Restitution & apology guidance provides actionable steps."""
        res = self.client.post(
            "/api/confessions/text",
            json={"text": "Jeg skylder min onkel penge fra et lån, som jeg nægtede at have taget.", "consent": True}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsNotNone(data.get("restitution_guidance"))
        self.assertIsNotNone(data.get("apology_guidance"))

    # ------------------------------------------------------------------------
    # Tier 2: Boundary & Corner Cases on Rights
    # ------------------------------------------------------------------------
    @tier(2)
    @requires_app
    def test_rights_boundary_deceased_victim(self):
        """Tier 2: Feature #40 - Restitution when victim has passed away (heirs / charity)."""
        res_deceased = self.client.post(
            "/api/confessions/text",
            json={"text": "Jeg stjal fra en ældre mand for ti år siden. Han er nu død. Hvordan giver jeg pengene tilbage?", "consent": True}
        )
        self.assertEqual(res_deceased.status_code, 200)
        data = res_deceased.json()
        restitution = (data.get("restitution_guidance") or "").lower()
        # Must mention heirs (arvinger) or charity (sadaqah / velgørenhed) in his name
        self.assertTrue(any(w in restitution for w in ["arvinger", "velgørenhed", "sadaqah", "dødsbo"]))

    @tier(2)
    @requires_app
    def test_rights_boundary_sitr_absolute_prohibition_of_public_exposure(self):
        """Tier 2: Feature #40 - Purely private sins must NEVER suggest public confession."""
        res_private = self.client.post(
            "/api/confessions/text",
            json={"text": "Jeg begik en personlig synd i hemmelighed som kun Allah kender til.", "consent": True}
        )
        self.assertEqual(res_private.status_code, 200)
        data = res_private.json()
        self.assertEqual(data["sin_classification"], "huqooq_allah")
        # Ensure apology guidance does not say 'go tell people'
        apology = (data.get("apology_guidance") or "").lower()
        self.assertTrue("fortæl" not in apology or "ikke" in apology or "skjul" in apology or len(apology) == 0)

    # ------------------------------------------------------------------------
    # Tier 3: Cross-Feature Interactions & Multi-Sin Splitting
    # ------------------------------------------------------------------------
    @tier(3)
    @requires_app
    def test_compound_confession_incident_splitting(self):
        """Tier 3: Feature #8 - Splits multi-sin confession into discrete incidents."""
        compound_text = (
            "I går begik jeg to store fejl. Først stjal jeg 500 kr fra min vens taske på arbejdet. "
            "Senere på aftenen blev jeg så fortvivlet, at jeg drak alkohol og sprang Isha-bønnen over."
        )
        res = self.client.post("/api/confessions/text", json={"text": compound_text, "consent": True})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        incidents = data.get("incidents", [])
        self.assertTrue(len(incidents) >= 2, f"Expected at least 2 incidents, got {len(incidents)}")

        # First incident: theft (both)
        theft_inc = [inc for inc in incidents if "stjal" in inc["description"].lower() or "500" in inc["description"]]
        if theft_inc:
            self.assertEqual(theft_inc[0]["sin_classification"], "both")

        # Second incident: alcohol / prayer (huqooq_allah)
        prayer_inc = [inc for inc in incidents if "bøn" in inc["description"].lower() or "alkohol" in inc["description"].lower()]
        if prayer_inc:
            self.assertEqual(prayer_inc[0]["sin_classification"], "huqooq_allah")

    @tier(3)
    @requires_app
    def test_apology_vs_fitnah_avoidance_rules(self):
        """Tier 3: Feature #12 - Apology nuance: avoid causing greater harm (Fitnah)."""
        backbiting_text = (
            "Jeg talte grimt om en kollegas familie bag hendes ryg. Hun ved intet om det. "
            "Hvis jeg fortæller hende det, vil hun blive knust og vores afdeling vil gå i opløsning."
        )
        res = self.client.post("/api/confessions/text", json={"text": backbiting_text, "consent": True})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        apology_guidance = (data.get("apology_guidance") or "").lower()
        # Must mention prioritizing fitnah avoidance, seeking forgiveness through dua and praising her
        self.assertTrue(any(w in apology_guidance for w in ["fitnah", "splid", "dua", "bøn", "rose", "undlade"]))

    @tier(3)
    @requires_app
    def test_anonymous_restitution_guidance(self):
        """Tier 3: Feature #13 - Guidance for returning stolen property anonymously."""
        theft_text = (
            "Jeg stjal en bærbar computer fra min tidligere arbejdsplads. "
            "Jeg vil give den tilbage, men frygter fængselsstraf og vanære."
        )
        res = self.client.post("/api/confessions/text", json={"text": theft_text, "consent": True})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        restitution_guidance = (data.get("restitution_guidance") or "").lower()
        self.assertTrue(any(w in restitution_guidance for w in ["anonym", "post", "bud", "tredjepart", "diskret"]))


if __name__ == "__main__":
    unittest.main()
