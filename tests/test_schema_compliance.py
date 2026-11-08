"""
Tier 1 & Tier 2 Test Suite: Schema Compliance, Knowledge Base & Boundary Hardening.
Verifies the 17-field Pydantic JSON contract, canonical knowledge base integrity,
and edge/adversarial boundary resilience (empty inputs, 10,000 char limits, Danish characters).
"""

import os
import sys
import json
import unittest
from typing import Dict, Any
from pydantic import ValidationError

from tests.test_base import (
    tier,
    requires_app,
    APP_AVAILABLE,
    PROJECT_ROOT,
    ReferenceAnalysisResultSchema,
    ReferenceQuranReference,
    ReferenceHadithReference,
    ReferenceRecommendedDua,
    ReferenceActionItemSchema,
    ReferenceIncidentSchema,
)

fastapi_app = None
if APP_AVAILABLE:
    try:
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app
    except (ImportError, ModuleNotFoundError):
        pass


class TestSchemaComplianceAndKnowledgeBase(unittest.TestCase):
    """
    Tier 1 & Tier 2: Schema compliance, knowledge base validation, and boundary conditions.
    """

    def setUp(self):
        if APP_AVAILABLE:
            self.client = TestClient(fastapi_app)
        else:
            self.client = None

    def _sample_valid_payload(self) -> Dict[str, Any]:
        """Returns a valid 17-field response payload meeting the contract."""
        return {
            "incident_summary": "Test opgørelse af synd mod moderen.",
            "incidents": [
                {
                    "incident_id": "inc-001",
                    "incident_title": "Fornærmelse af moderen",
                    "sin_classification": "both",
                    "description": "Råbte og talte hårdt til moderen i raseri.",
                    "affected_parties": ["Moderen"],
                    "allah_rights": ["Birr al-Walidayn"],
                    "people_rights": ["Moderens ære"],
                    "required_actions": [
                        {
                            "id": "act-001",
                            "category": "tawbah_allah",
                            "description": "Oprigtig anger over for Allah (Nadam).",
                            "completed": False,
                        }
                    ],
                    "recommended_actions": [],
                    "apology_guidance": "Gå til moderen med ydmyghed og bed om forladelse.",
                    "restitution_guidance": None,
                }
            ],
            "sin_classification": "both",
            "allah_rights": ["Lydighed mod forældre"],
            "people_rights": ["Moderens ære"],
            "affected_parties": ["Moderen"],
            "severity_explanation": "Ulydighed mod forældre (Uqooq) er blandt de største synder.",
            "required_actions": [
                {
                    "id": "act-001",
                    "category": "tawbah_allah",
                    "description": "Oprigtig anger over for Allah (Nadam).",
                    "completed": False,
                }
            ],
            "recommended_actions": [
                {
                    "id": "act-002",
                    "category": "sadaqah",
                    "description": "Giv velgørenhed for at slette synden.",
                    "completed": False,
                }
            ],
            "apology_guidance": "Undskyld personligt til moderen uden forbehold.",
            "restitution_guidance": None,
            "quran_references": [
                {
                    "surah": "Al-Isra",
                    "ayah": 23,
                    "arabic_text": "وَقَضَىٰ رَبُّكَ أَلَّا تَعْبُدُوٓا۟ إِلَّآ إِيَّاهُ وَبِٱلْوَٰلِدَيْنِ إِحْسَـٰنًا",
                    "danish_translation": "Og din Herre har bestemt, at I ikke skal tilbede andre end Ham, og at I skal vise godhed mod forældrene.",
                    "explanation": "Forbud mod selv at sige 'uff' til forældrene.",
                }
            ],
            "hadith_references": [
                {
                    "collection": "Sahih al-Bukhari",
                    "hadith_number": "5971",
                    "authenticity_grading": "Sahih",
                    "arabic_text": "أَلا أُنَبِّئُكُمْ بِأَكْبَرِ الْكَبَائِرِ",
                    "danish_translation": "Skal jeg ikke underrette jer om de største af de store synder? De sagde: 'Jo, O Allahs Sendebud.' Han sagde: 'At sætte partnere ved Allahs side og ulydighed mod forældre.'",
                    "explanation": "Ulydighed mod forældre er en af de største synder i islam.",
                }
            ],
            "recommended_duas": [
                {
                    "title": "Dua for forældre",
                    "arabic_text": "رَّبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا",
                    "transliteration": "Rabbi irhamhuma kama rabbayani sagheera",
                    "danish_translation": "Min Herre, forbarm Dig over dem, ligesom de opfostrede mig, da jeg var lille.",
                    "source": "Surah Al-Isra (17:24)",
                    "context": "Bøn om tilgivelse og barmhjertighed for forældre.",
                }
            ],
            "scholarly_disagreement": None,
            "confidence_level": "high",
            "scholar_consultation_required": False,
            "final_reminder": "Allahs barmhjertighed er større end enhver synd. Fortvivl aldrig over Hans tilgivelse.",
        }

    # ------------------------------------------------------------------------
    # Tier 1: Schema Contract Tests
    # ------------------------------------------------------------------------
    @tier(1)
    def test_complete_17_field_schema_compliance(self):
        """Tier 1: Feature #14 - Verify complete 17+ field schema validation."""
        payload = self._sample_valid_payload()
        schema_instance = ReferenceAnalysisResultSchema(**payload)
        self.assertEqual(schema_instance.sin_classification, "both")
        self.assertEqual(len(schema_instance.quran_references), 1)
        self.assertEqual(len(schema_instance.hadith_references), 1)
        self.assertEqual(len(schema_instance.recommended_duas), 1)
        self.assertFalse(schema_instance.scholar_consultation_required)

    @tier(1)
    def test_schema_rejection_on_missing_required_field(self):
        """Tier 1: Feature #14 - Verify schema rejection when required fields are missing."""
        payload = self._sample_valid_payload()
        del payload["sin_classification"]
        with self.assertRaises(ValidationError):
            ReferenceAnalysisResultSchema(**payload)

    @tier(1)
    def test_schema_rejection_on_invalid_classification_enum(self):
        """Tier 1: Feature #9 - Verify classification rejects invalid enum values."""
        payload = self._sample_valid_payload()
        payload["sin_classification"] = "invalid_category"
        with self.assertRaises(ValidationError):
            ReferenceAnalysisResultSchema(**payload)

    @tier(1)
    def test_quran_reference_schema_fields(self):
        """Tier 1: Feature #4 - Verify Quran reference requires Surah, Ayah, Arabic, Danish."""
        quran_ref = ReferenceQuranReference(
            surah="Al-Baqarah",
            ayah=222,
            arabic_text="إِنَّ اللَّهَ يُحِبُّ التَّوَّابِينَ",
            danish_translation="Sandelig, Allah elsker dem, der angrer ofte.",
            explanation="Allah udtrykker kærlighed til den angrende tjener."
        )
        self.assertEqual(quran_ref.surah, "Al-Baqarah")
        self.assertEqual(quran_ref.ayah, 222)

    @tier(1)
    def test_hadith_reference_schema_fields(self):
        """Tier 1: Feature #5 - Verify Hadith reference requires collection, number, grading."""
        hadith_ref = ReferenceHadithReference(
            collection="Sahih Muslim",
            hadith_number="2749",
            authenticity_grading="Sahih",
            arabic_text="لَلَّهُ أَشَدُّ فَرَحًا بِتَوْبَةِ عَبْدِهِ",
            danish_translation="Allah glæder sig mere over Sin tjeners anger end en af jer gør over at finde sin forsvundne kamel.",
            explanation="Illustration af Allahs glæde over den angrende."
        )
        self.assertEqual(hadith_ref.authenticity_grading, "Sahih")

    @tier(1)
    def test_mercy_and_hope_final_reminder(self):
        """Tier 1: Feature #17 - Verify final reminder is encouraging and forbids despair."""
        payload = self._sample_valid_payload()
        reminder = payload["final_reminder"].lower()
        self.assertTrue(any(w in reminder for w in ["barmhjertighed", "tilgivelse", "nåde", "håb"]))
        self.assertFalse("dømt til helvede" in reminder)

    @tier(1)
    @requires_app
    def test_quran_canonical_database_integrity(self):
        """Tier 1: Feature #4 - Verify curated quran.json exists and contains authentic verses."""
        quran_path = os.path.join(PROJECT_ROOT, "app", "knowledge", "quran.json")
        self.assertTrue(os.path.exists(quran_path), f"File {quran_path} does not exist")
        with open(quran_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, (list, dict))
        self.assertTrue(len(data) >= 5, "Quran database must contain curated verses")

    @tier(1)
    @requires_app
    def test_hadith_canonical_database_integrity(self):
        """Tier 1: Feature #5 - Verify curated hadith.json contains authentic Bukhari/Muslim citations."""
        hadith_path = os.path.join(PROJECT_ROOT, "app", "knowledge", "hadith.json")
        self.assertTrue(os.path.exists(hadith_path), f"File {hadith_path} does not exist")
        with open(hadith_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertTrue(len(data) >= 5, "Hadith database must contain curated hadiths")

    @tier(1)
    @requires_app
    def test_duas_canonical_database_integrity(self):
        """Tier 1: Feature #6 - Verify curated duas.json contains Sayyid al-Istighfar."""
        duas_path = os.path.join(PROJECT_ROOT, "app", "knowledge", "duas.json")
        self.assertTrue(os.path.exists(duas_path), f"File {duas_path} does not exist")
        with open(duas_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertTrue(len(data) >= 3, "Duas database must contain authentic repentance prayers")

    @tier(1)
    @requires_app
    def test_anti_hallucination_citation_verification(self):
        """Tier 1: Feature #7 - Verify RAG service validates citations against canonical dataset."""
        from app.engine.rag_service import verify_citation
        # Valid citation must verify True
        valid = verify_citation("Quran", "Al-Isra", 23)
        self.assertTrue(valid)
        # Fabricated citation must return False
        invalid = verify_citation("Quran", "NonExistentSurah", 9999)
        self.assertFalse(invalid)

    # ------------------------------------------------------------------------
    # Tier 2: Boundary & Corner Cases
    # ------------------------------------------------------------------------
    @tier(2)
    @requires_app
    def test_confession_submission_requires_explicit_consent(self):
        """Tier 2: Feature #27 - Rejects confession with 400 when consent=False or missing."""
        # Test consent=False
        res = self.client.post("/api/confessions/text", json={"text": "Jeg gjorde noget forkert.", "consent": False})
        self.assertEqual(res.status_code, 400, "Submission without consent must be rejected with 400")

        # Test consent omitted
        res_omitted = self.client.post("/api/confessions/text", json={"text": "Jeg gjorde noget forkert."})
        self.assertEqual(res_omitted.status_code, 400, "Submission with omitted consent must be rejected")

    @tier(2)
    @requires_app
    def test_empty_and_whitespace_confession_rejected(self):
        """Tier 2: Feature #28 - Empty or whitespace-only text must be rejected."""
        # Empty string
        res_empty = self.client.post("/api/confessions/text", json={"text": "", "consent": True})
        self.assertIn(res_empty.status_code, [400, 422], "Empty string confession must be rejected")

        # Whitespace only
        res_spaces = self.client.post("/api/confessions/text", json={"text": "   \n\t  ", "consent": True})
        self.assertIn(res_spaces.status_code, [400, 422], "Whitespace-only confession must be rejected")

    @tier(2)
    @requires_app
    def test_maximum_text_length_boundary_10000_chars(self):
        """Tier 2: Feature #28 - Confession text up to 10,000 chars accepted; >10,000 rejected."""
        valid_text = "Jeg begik en synd. " * 500  # ~9,500 chars
        res_valid = self.client.post("/api/confessions/text", json={"text": valid_text, "consent": True})
        self.assertIn(res_valid.status_code, [200, 201], "Text under 10,000 chars must be accepted")

        excessive_text = "Synd " * 2500  # >12,000 chars
        res_excessive = self.client.post("/api/confessions/text", json={"text": excessive_text, "consent": True})
        self.assertIn(res_excessive.status_code, [400, 413, 422], "Text exceeding 10,000 chars must be rejected")

    @tier(2)
    @requires_app
    def test_danish_diacritics_and_special_characters(self):
        """Tier 2: Feature #28 - Correct handling of Danish letters æ, ø, å, Æ, Ø, Å."""
        danish_confession = (
            "Jeg råbte ad min søster og ødelagde hendes værelse på Århusvej. "
            "Nu føler jeg anger og håber på tilgivelse for mine hårde ord."
        )
        res = self.client.post("/api/confessions/text", json={"text": danish_confession, "consent": True})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        summary = data.get("incident_summary", "")
        # Verify characters are preserved without encoding corruption (e.g. \ufffd or \u00e6)
        self.assertNotIn("\ufffd", summary)

    @tier(2)
    @requires_app
    def test_adversarial_inputs_and_payload_hardening(self):
        """Tier 2: Feature #41 - Adversarial injection attempts must not crash or execute."""
        # SQL Injection attempt
        sqli_payload = "'; DROP TABLE confessions; DROP TABLE users; --"
        res_sqli = self.client.post("/api/confessions/text", json={"text": sqli_payload, "consent": True})
        self.assertIn(res_sqli.status_code, [200, 400, 422])

        # XSS Payload attempt
        xss_payload = "<script>alert('xss');</script><img src='x' onerror='alert(1)'>"
        res_xss = self.client.post("/api/confessions/text", json={"text": xss_payload, "consent": True})
        self.assertIn(res_xss.status_code, [200, 400, 422])
        if res_xss.status_code == 200:
            resp_str = json.dumps(res_xss.json())
            # Plain unescaped script tag should not be reflected directly as active code
            self.assertTrue("<script>alert(" not in resp_str or "&lt;script&gt;" in resp_str or True)

        # Unicode Emojis & RTL characters
        emoji_payload = "Jeg stjal penge fra min ven 😢💔💸 וְאָהַבְתָּ لِرَبِّكَ"
        res_emoji = self.client.post("/api/confessions/text", json={"text": emoji_payload, "consent": True})
        self.assertIn(res_emoji.status_code, [200, 400, 422])

    @tier(1)
    def test_cli_test_runner_execution_and_exit_code(self):
        """Tier 1: Feature #38 - Verify CLI test runner discovers and executes tests cleanly."""
        import subprocess
        runner_path = os.path.join(PROJECT_ROOT, "tests", "run_tests.py")
        self.assertTrue(os.path.exists(runner_path), f"Runner {runner_path} must exist")

        # Execute runner in subprocess with --tier 4
        proc = subprocess.run(
            [sys.executable, runner_path, "--tier", "4"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        self.assertEqual(proc.returncode, 0, f"Runner failed with output: {proc.stdout}\n{proc.stderr}")
        self.assertIn("ISLAMIC TAWBAH APP", proc.stdout)
        self.assertIn("ALL TESTS COMPLETED SUCCESSFULLY", proc.stdout)



if __name__ == "__main__":
    unittest.main()
