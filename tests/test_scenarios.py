"""
Tier 4 Test Suite: The 10 Required Confession Scenarios (Section 13 / R5).
Verifies rights classification, affected parties, Tawbah conditions,
apology/restitution fiqh nuances, and authentic Quran/Hadith evidence.
"""

import unittest
from typing import Dict, Any

from tests.test_base import (
    tier,
    requires_app,
    APP_AVAILABLE,
    TEN_SCENARIOS,
    ReferenceAnalysisResultSchema,
)

fastapi_app = None
if APP_AVAILABLE:
    try:
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app
    except (ImportError, ModuleNotFoundError):
        pass


class TestTenConfessionScenarios(unittest.TestCase):
    """
    Tier 4: Comprehensive validation of all 10 canonical confession scenarios.
    Ensures strict adherence to classical Ahlus-Sunnah wal-Jama'ah fiqh jurisprudence.
    """

    def setUp(self):
        if APP_AVAILABLE:
            self.client = TestClient(fastapi_app)
        else:
            self.client = None

    def _execute_scenario(self, scenario_id: int) -> Dict[str, Any]:
        """Helper to invoke API or rule engine for a scenario."""
        scenario = TEN_SCENARIOS[scenario_id]
        response = self.client.post(
            "/api/confessions/text",
            json={"text": scenario["input_text"], "consent": True}
        )
        self.assertEqual(response.status_code, 200, f"API returned status {response.status_code}")
        data = response.json()
        return data

    # ------------------------------------------------------------------------
    # Scenario 1: Fornærmelse af moderen (Insulting Mother)
    # ------------------------------------------------------------------------
    @tier(4)
    def test_scenario_01_insulting_mother_contract(self):
        """Tier 4: Scenario 1 - Contract specification check for insulting mother."""
        sc = TEN_SCENARIOS[1]
        self.assertEqual(sc["expected_classification"], "both")
        self.assertIn("Moderen", sc["affected_parties"])
        self.assertEqual(sc["quran_surah"], "Al-Isra")
        self.assertEqual(sc["quran_ayah"], 23)

    @tier(4)
    @requires_app
    def test_scenario_01_insulting_mother_execution(self):
        """Tier 4: Scenario 1 - Live engine execution for insulting mother."""
        data = self._execute_scenario(1)
        self.assertEqual(data["sin_classification"], "both")
        self.assertTrue(any("mor" in p.lower() for p in data["affected_parties"]))
        # Required actions must include direct apology and no fitnah exemption
        all_req_text = " ".join([a["description"].lower() + " " + a.get("explanation", "").lower()
                                 for a in data["required_actions"]])
        self.assertTrue(any(k in all_req_text for k in ["undskyld", "tilgivelse", "forældre", "mor"]))
        # Check Quran citation contains Al-Isra
        quran_surahs = [q["surah"].lower() for q in data["quran_references"]]
        self.assertTrue(any("isra" in s for s in quran_surahs))

    # ------------------------------------------------------------------------
    # Scenario 2: Tyveri fra faderen (Stealing from Father)
    # ------------------------------------------------------------------------
    @tier(4)
    def test_scenario_02_stealing_from_father_contract(self):
        """Tier 4: Scenario 2 - Contract specification check for stealing from father."""
        sc = TEN_SCENARIOS[2]
        self.assertEqual(sc["expected_classification"], "both")
        self.assertIn("Faderen", sc["affected_parties"])
        self.assertEqual(sc["quran_surah"], "Al-Ma'idah")
        self.assertEqual(sc["hadith_collection"], "Sahih al-Bukhari")

    @tier(4)
    @requires_app
    def test_scenario_02_stealing_from_father_execution(self):
        """Tier 4: Scenario 2 - Live engine execution for stealing from father."""
        data = self._execute_scenario(2)
        self.assertEqual(data["sin_classification"], "both")
        self.assertTrue(any("far" in p.lower() for p in data["affected_parties"]))
        # Must require financial restitution (radd al-mazalim)
        all_req_text = " ".join([a["description"].lower() + " " + a.get("explanation", "").lower()
                                 for a in data["required_actions"]])
        self.assertTrue(any(k in all_req_text for k in ["tilbage", "penge", "restitution", "beløb", "2.000", "2000"]))
        # Nuance: restitution guidance must permit secret/anonymous return to prevent family breakdown
        guidance = (data.get("restitution_guidance") or "").lower()
        self.assertTrue(any(k in guidance for k in ["anonym", "hemmelig", "pung", "diskret", "uden at konfrontere"]))

    # ------------------------------------------------------------------------
    # Scenario 3: Bagtalelse (Backbiting / Ghibah)
    # ------------------------------------------------------------------------
    @tier(4)
    def test_scenario_03_backbiting_ghibah_contract(self):
        """Tier 4: Scenario 3 - Contract specification check for backbiting."""
        sc = TEN_SCENARIOS[3]
        self.assertEqual(sc["expected_classification"], "both")
        self.assertEqual(sc["quran_surah"], "Al-Hujurat")
        self.assertEqual(sc["quran_ayah"], 12)

    @tier(4)
    @requires_app
    def test_scenario_03_backbiting_ghibah_execution(self):
        """Tier 4: Scenario 3 - Live engine execution for backbiting with fitnah nuance."""
        data = self._execute_scenario(3)
        self.assertEqual(data["sin_classification"], "both")
        # Nuance: Apology vs Fitnah prevention: if victim unaware, do NOT cause strife; make dua and praise them
        guidance = ((data.get("apology_guidance") or "") + " " +
                    (data.get("scholarly_disagreement") or "") + " " +
                    " ".join([a["description"] for a in data["required_actions"]])).lower()
        self.assertTrue(any(k in guidance for k in ["fitnah", "dua", "bøn", "rose", "tie", "videre"]))

    # ------------------------------------------------------------------------
    # Scenario 4: Manglende Fajr-bøn bevidst (Missing Fajr Intentionally)
    # ------------------------------------------------------------------------
    @tier(4)
    def test_scenario_04_missing_fajr_contract(self):
        """Tier 4: Scenario 4 - Contract specification check for missing Fajr."""
        sc = TEN_SCENARIOS[4]
        self.assertEqual(sc["expected_classification"], "huqooq_allah")
        self.assertEqual(sc["affected_parties"], [])

    @tier(4)
    @requires_app
    def test_scenario_04_missing_fajr_execution(self):
        """Tier 4: Scenario 4 - Live engine execution for missing Fajr intentionally."""
        data = self._execute_scenario(4)
        # MUST be purely Huqooq Allah
        self.assertEqual(data["sin_classification"], "huqooq_allah")
        # Zero human victims
        self.assertEqual(len(data.get("affected_parties", [])), 0)
        self.assertEqual(len(data.get("people_rights", [])), 0)
        # Required actions must include Qada (make-up prayer)
        all_req_text = " ".join([a["description"].lower() + " " + a.get("explanation", "").lower()
                                 for a in data["required_actions"]])
        self.assertTrue(any(k in all_req_text for k in ["qada", "indhent", "bøn", "fajr"]))
        # No human restitution or apology required
        self.assertTrue(data.get("apology_guidance") is None or "ikke relevant" in data["apology_guidance"].lower() or len(data["apology_guidance"]) == 0)

    # ------------------------------------------------------------------------
    # Scenario 5: Løgn overfor ægtefælle (Lying to Spouse)
    # ------------------------------------------------------------------------
    @tier(4)
    def test_scenario_05_lying_to_spouse_contract(self):
        """Tier 4: Scenario 5 - Contract specification check for lying to spouse."""
        sc = TEN_SCENARIOS[5]
        self.assertEqual(sc["expected_classification"], "both")
        self.assertIn("Ægtefællen", sc["affected_parties"])
        self.assertEqual(sc["quran_surah"], "At-Tawbah")

    @tier(4)
    @requires_app
    def test_scenario_05_lying_to_spouse_execution(self):
        """Tier 4: Scenario 5 - Live engine execution for lying to spouse."""
        data = self._execute_scenario(5)
        self.assertEqual(data["sin_classification"], "both")
        self.assertTrue(any("ægtefælle" in p.lower() for p in data["affected_parties"]))
        # Actions must emphasize truthfulness, reconciliation, and rebuilding trust
        all_req_text = " ".join([a["description"].lower() + " " + a.get("explanation", "").lower()
                                 for a in data["required_actions"]])
        self.assertTrue(any(k in all_req_text for k in ["sandhed", "ærlighed", "tillid", "undskyld"]))

    # ------------------------------------------------------------------------
    # Scenario 6: Hærværk / Skade på naboens ejendom (Damaging Property)
    # ------------------------------------------------------------------------
    @tier(4)
    def test_scenario_06_damaging_property_contract(self):
        """Tier 4: Scenario 6 - Contract specification check for damaging property."""
        sc = TEN_SCENARIOS[6]
        self.assertEqual(sc["expected_classification"], "both")
        self.assertIn("Naboen", sc["affected_parties"])
        self.assertEqual(sc["quran_surah"], "An-Nisa")

    @tier(4)
    @requires_app
    def test_scenario_06_damaging_property_execution(self):
        """Tier 4: Scenario 6 - Live engine execution for damaging neighbor's property."""
        data = self._execute_scenario(6)
        self.assertEqual(data["sin_classification"], "both")
        self.assertTrue(any("nabo" in p.lower() for p in data["affected_parties"]))
        # Restitution/compensation is mandatory (Daman)
        all_req_text = " ".join([a["description"].lower() + " " + a.get("explanation", "").lower()
                                 for a in data["required_actions"]])
        self.assertTrue(any(k in all_req_text for k in ["erstatning", "reparation", "betal", "dække"]))

    # ------------------------------------------------------------------------
    # Scenario 7: Tilbagelevering af uretmæssigt tilegnede penge (Anonymous Restitution)
    # ------------------------------------------------------------------------
    @tier(4)
    def test_scenario_07_anonymous_restitution_contract(self):
        """Tier 4: Scenario 7 - Contract specification check for anonymous restitution."""
        sc = TEN_SCENARIOS[7]
        self.assertEqual(sc["expected_classification"], "both")
        self.assertEqual(sc["quran_surah"], "An-Nisa")
        self.assertEqual(sc["quran_ayah"], 58)

    @tier(4)
    @requires_app
    def test_scenario_07_anonymous_restitution_execution(self):
        """Tier 4: Scenario 7 - Live engine execution for anonymous restitution."""
        data = self._execute_scenario(7)
        self.assertEqual(data["sin_classification"], "both")
        # Restitution guidance MUST explicitly confirm that returning money anonymously is valid
        restitution_guidance = (data.get("restitution_guidance") or "").lower()
        self.assertTrue(any(k in restitution_guidance for k in ["anonym", "diskret", "tredjepart", "overførsel", "konvolut"]))

    # ------------------------------------------------------------------------
    # Scenario 8: Privat synd mellem tjener og Allah (Private Sin - Sitr)
    # ------------------------------------------------------------------------
    @tier(4)
    def test_scenario_08_private_sin_sitr_contract(self):
        """Tier 4: Scenario 8 - Contract specification check for private sin."""
        sc = TEN_SCENARIOS[8]
        self.assertEqual(sc["expected_classification"], "huqooq_allah")
        self.assertEqual(sc["affected_parties"], [])
        self.assertEqual(sc["hadith_collection"], "Sahih al-Bukhari")
        self.assertEqual(sc["hadith_number"], "6069")

    @tier(4)
    @requires_app
    def test_scenario_08_private_sin_sitr_execution(self):
        """Tier 4: Scenario 8 - Live engine execution for private sin (Mandatory Sitr)."""
        data = self._execute_scenario(8)
        self.assertEqual(data["sin_classification"], "huqooq_allah")
        self.assertEqual(len(data.get("affected_parties", [])), 0)
        # Mandatory Sitr: STRICTLY PROHIBITED to confess or expose to humans
        all_text = ((data.get("severity_explanation") or "") + " " +
                    (data.get("apology_guidance") or "") + " " +
                    " ".join([a["description"] for a in data["required_actions"]])).lower()
        self.assertTrue(any(k in all_text for k in ["sitr", "hemmelighold", "skjul", "fortæl ikke", "ingen mennesker"]))

    # ------------------------------------------------------------------------
    # Scenario 9: Falsk anklage / Bagvaskelse (False Accusation / Buhtan)
    # ------------------------------------------------------------------------
    @tier(4)
    def test_scenario_09_false_accusation_buhtan_contract(self):
        """Tier 4: Scenario 9 - Contract specification check for false accusation."""
        sc = TEN_SCENARIOS[9]
        self.assertEqual(sc["expected_classification"], "both")
        self.assertIn("Den falsk anklagede person", sc["affected_parties"])
        self.assertEqual(sc["quran_surah"], "An-Nur")

    @tier(4)
    @requires_app
    def test_scenario_09_false_accusation_buhtan_execution(self):
        """Tier 4: Scenario 9 - Live engine execution for false accusation (Public Retraction)."""
        data = self._execute_scenario(9)
        self.assertEqual(data["sin_classification"], "both")
        # Mandatory public retraction to the exact listeners to clear victim's honor
        all_req_text = " ".join([a["description"].lower() + " " + a.get("explanation", "").lower()
                                 for a in data["required_actions"]]).lower()
        self.assertTrue(any(k in all_req_text for k in ["offentlig", "træk", "tilbage", "rense", "tilbagetræk", "vidner"]))

    # ------------------------------------------------------------------------
    # Scenario 10: Brud på tillid / Underslæb (Breaking Trust / Embezzlement)
    # ------------------------------------------------------------------------
    @tier(4)
    def test_scenario_10_embezzlement_amanah_contract(self):
        """Tier 4: Scenario 10 - Contract specification check for embezzlement."""
        sc = TEN_SCENARIOS[10]
        self.assertEqual(sc["expected_classification"], "both")
        self.assertEqual(sc["quran_surah"], "Al-Anfal")
        self.assertEqual(sc["quran_ayah"], 27)

    @tier(4)
    @requires_app
    def test_scenario_10_embezzlement_amanah_execution(self):
        """Tier 4: Scenario 10 - Live engine execution for embezzlement of trust."""
        data = self._execute_scenario(10)
        self.assertEqual(data["sin_classification"], "both")
        # Financial restitution into treasury and stepping down
        all_req_text = " ".join([a["description"].lower() + " " + a.get("explanation", "").lower()
                                 for a in data["required_actions"]]).lower()
        self.assertTrue(any(k in all_req_text for k in ["tilbage", "kasse", "konto", "forening", "restitution", "15.000", "15000"]))


if __name__ == "__main__":
    unittest.main()
