"""
tests/test_challenger2_m1_it3_stress.py

Empirical Challenger 2 Stress Harness for Milestone 1 Iteration 3:
Examines citation boundaries, anti-hallucination sanitization,
edge cases (empty strings, NoneType inputs, long Unicode texts, hostile prefixes, type safety).
"""

import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.rag_service import (
    IslamicRAGService,
    get_rag_service,
    verify_citation,
    normalize_text,
    normalize_arabic,
    resolve_hadith_collection_family,
)
from app.schemas import AnalysisResultSchema


class TestMilestone1Iteration3Stress(unittest.TestCase):
    """Deep empirical boundary tests for RAG service and citation verification."""

    def setUp(self):
        self.rag = get_rag_service()

    def test_empty_and_nonetype_inputs(self):
        """All empty strings, whitespaces, and NoneType inputs must be rejected safely without crashing."""
        edge_cases = [
            (None, None, None),
            ("", "", ""),
            ("   ", "   ", "   "),
            ("\t\n", "\t\n", "\t\n"),
            ("Quran", "", 53),
            ("Quran", None, 53),
            ("Quran", "Az-Zumar", None),
            ("Quran", "Az-Zumar", ""),
            ("Quran", "Az-Zumar", "   "),
            ("Hadith", "", 2449),
            ("Hadith", None, 2449),
            ("Hadith", "Bukhari", None),
            ("Hadith", "Bukhari", ""),
            ("Hadith", "Bukhari", "   "),
            (None, "Bukhari", 2449),
            ("", "Bukhari", 2449),
            ("   ", "Bukhari", 2449),
        ]
        for st, idf, num in edge_cases:
            self.assertFalse(
                verify_citation(st, idf, num),
                f"verify_citation({st!r}, {idf!r}, {num!r}) must return False",
            )

    def test_long_unicode_and_injection_payloads(self):
        """Long Unicode, Zalgo, Arabic diacritics, and injection strings must not crash."""
        zalgo = "Az-Zumar" + "\u0300\u0301\u0302\u0303\u0304" * 1000
        arabic_diacritics = "الزمر" + "\u0651\u064e\u0650\u064f" * 1000
        extreme_whitespace = "   " * 3000 + "Az-Zumar" + "   " * 3000
        null_byte = "Az-Zumar\x00"
        bidi = "\u202e" + "Sahih al-Bukhari" + "\u202c"

        # Citation checks
        self.assertFalse(verify_citation("Quran", zalgo, 53))
        self.assertFalse(verify_citation("Quran", null_byte, 53))
        self.assertFalse(verify_citation("Hadith", bidi, 2449))
        self.assertTrue(verify_citation("Quran", extreme_whitespace, 53))

        # Search methods under extreme length
        res_q = self.rag.search_quran(query=zalgo)
        self.assertIsInstance(res_q, list)
        res_h = self.rag.search_hadith(query=arabic_diacritics)
        self.assertIsInstance(res_h, list)
        res_d = self.rag.search_duas(query="Sayyid" + " " * 5000 + "al-Istighfar")
        self.assertIsInstance(res_d, list)

    def test_search_category_type_safety(self):
        """Passing non-string category (e.g. int, list, None) should not crash with AttributeError."""
        # None should be handled safely
        res_none_q = self.rag.search_quran(category=None)
        self.assertIsInstance(res_none_q, list)
        res_none_h = self.rag.search_hadith(category=None)
        self.assertIsInstance(res_none_h, list)
        res_none_d = self.rag.search_duas(category=None)
        self.assertIsInstance(res_none_d, list)

    def test_adversarial_hostile_hadith_collection_names(self):
        """
        Adversarial test: Hostile, fabricated, or negated collection names containing
        canonical substrings ('Non-Muslim', 'Anti-Bukhari', 'Fake Bukhari', 'Devil Bukhari')
        must NOT be accepted as authentic canonical collections!
        """
        hostile_cases = [
            ("Non-Muslim", 2581),
            ("Anti-Muslim", 2581),
            ("Ex-Muslim", 2581),
            ("Anti-Bukhari", 2449),
            ("Fake Bukhari", 2449),
            ("Pseudo-Bukhari", 2449),
            ("Not Bukhari", 2449),
            ("Devil Bukhari", 2449),
            ("Fake Abu Dawud", 3561),
            ("Pseudo Ibn Majah", 4252),
        ]
        for coll, num in hostile_cases:
            is_valid = verify_citation("Hadith", coll, num)
            self.assertFalse(
                is_valid,
                f"VULNERABILITY: Hostile collection name '{coll}' was verified as canonical for Hadith {num}!",
            )

    def test_fabricated_quran_and_hadith_content_purged_in_sanitizer(self):
        """
        Adversarial test: If an incoming payload contains valid citations (e.g. Az-Zumar 53, Bukhari 2449)
        but contains fabricated Arabic text or Danish translations,
        validate_and_sanitize_analysis must purge or replace them with canonical content.
        """
        fake_quran = {
            "surah": "Az-Zumar",
            "ayah": 53,
            "arabic_text": "قُلْ يَا أَيُّهَا الْكَافِرُونَ هَذَا نَصٌّ مُفْتَرًى",
            "danish_translation": "Falsk og opdigtet dansk oversaettelse",
            "explanation": "Falsk forklaring",
        }
        fake_hadith = {
            "collection": "Sahih al-Bukhari",
            "hadith_number": "2449",
            "arabic_text": "نص حديث مكذوب ومفترى على النبي",
            "danish_translation": "Falsk oversaettelse af Bukhari 2449",
            "explanation": "Falsk forklaring",
            "authenticity_grading": "Mawdu (Opdigtet)",
        }
        sanitized = self.rag.validate_and_sanitize_analysis({
            "quran_references": [fake_quran],
            "hadith_references": [fake_hadith],
        })

        out_quran = sanitized["quran_references"][0]
        out_hadith = sanitized["hadith_references"][0]

        self.assertNotEqual(
            out_quran.get("arabic_text"),
            "قُلْ يَا أَيُّهَا الْكَافِرُونَ هَذَا نَصٌّ مُفْتَرًى",
            "VULNERABILITY: Fabricated Quran Arabic text was preserved verbatim by sanitizer!",
        )
        self.assertNotEqual(
            out_quran.get("danish_translation"),
            "Falsk og opdigtet dansk oversaettelse",
            "VULNERABILITY: Fabricated Quran Danish translation was preserved verbatim by sanitizer!",
        )
        self.assertNotEqual(
            out_hadith.get("arabic_text"),
            "نص حديث مكذوب ومفترى على النبي",
            "VULNERABILITY: Fabricated Hadith Arabic text was preserved verbatim by sanitizer!",
        )
        self.assertNotEqual(
            out_hadith.get("danish_translation"),
            "Falsk oversaettelse af Bukhari 2449",
            "VULNERABILITY: Fabricated Hadith Danish translation was preserved verbatim by sanitizer!",
        )

    def test_partial_citation_dictionary_schema_compliance_after_sanitization(self):
        """
        Adversarial test: Incoming payloads with only citation identifiers (e.g. {'surah': 'Az-Zumar', 'ayah': 53})
        must be enriched with all required fields so that the resulting dictionary
        conforms to AnalysisResultSchema without validation errors.
        """
        payload = {
            "incident_summary": "Test incident",
            "incidents": [],
            "sin_classification": "huqooq_allah",
            "allah_rights": ["Ret"],
            "people_rights": [],
            "affected_parties": ["Allah"],
            "severity_explanation": "Forklaring",
            "required_actions": [],
            "recommended_actions": [],
            "quran_references": [{"surah": "Az-Zumar", "ayah": 53}],
            "hadith_references": [{"collection": "Sahih al-Bukhari", "hadith_number": "2449"}],
            "recommended_duas": [{"title": "Sayyid al-Istighfar"}],
            "confidence_level": "high",
            "scholar_consultation_required": False,
            "final_reminder": "Husk Allahs barmhjertighed",
        }
        sanitized = self.rag.validate_and_sanitize_analysis(payload)
        # Must conform to AnalysisResultSchema
        try:
            AnalysisResultSchema.model_validate(sanitized)
        except Exception as e:
            self.fail(f"VULNERABILITY: Sanitized dictionary failed AnalysisResultSchema validation: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
