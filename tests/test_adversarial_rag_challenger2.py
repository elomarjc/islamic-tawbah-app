"""
tests/test_adversarial_rag_challenger2.py

Empirical Challenger 2 Adversarial Stress Harness for Milestone 1 Iteration 2:
- Mandatory dispatch checks:
  * verify_citation('Hadith', '', 2449) == False
  * verify_citation('Hadith', '   ', 2449) == False
  * verify_citation('Hadith', 'sahih', 2449) == False
  * verify_citation with generic collection prefixes ('sunan', 'jami', 'musnad', 'kitab') == False
- Fabricated Duas verification & anti-hallucination sanitization stress
- Negative Hadith numbers and input type confusion
- Quran citation boundary testing (negative ayahs, out-of-range, None)
- Extreme Unicode diacritics, tatweel, and injection payloads
- Null fields and malformed payloads in validate_and_sanitize_analysis
"""

import sys
import unittest
from pathlib import Path
from typing import Any, Dict

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


class TestHadithCitationAdversarialStress(unittest.TestCase):
    """Stress tests on Hadith citation verification."""

    def setUp(self):
        self.rag = get_rag_service()

    def test_mandatory_dispatch_empty_and_whitespace_collections(self):
        """Empty and whitespace collection names must return False."""
        self.assertFalse(
            verify_citation("Hadith", "", 2449),
            "Empty collection name '' must return False",
        )
        self.assertFalse(
            verify_citation("Hadith", "   ", 2449),
            "Whitespace collection name '   ' must return False",
        )
        self.assertFalse(
            verify_citation("Hadith", "\t\n", 2449),
            "Tab/newline collection name must return False",
        )

    def test_mandatory_dispatch_generic_collection_names(self):
        """Generic collection terms without specific name must return False."""
        generic_terms = [
            "sahih",
            "sunan",
            "jami",
            "musnad",
            "kitab",
            "hadith",
            "ahadith",
            "sunnah",
            "imam",
            "kutub",
            "islam",
            "al-hadith",
        ]
        for term in generic_terms:
            self.assertFalse(
                verify_citation("Hadith", term, 2449),
                f"Generic collection term '{term}' with Bukhari 2449 must return False",
            )
            # Also test with other valid hadith numbers (Muslim 2581, Ibn Majah 4252, Abu Dawud 3561)
            self.assertFalse(
                verify_citation("Hadith", term, 2581),
                f"Generic collection term '{term}' with Muslim 2581 must return False",
            )
            self.assertFalse(
                verify_citation("Hadith", term, 4252),
                f"Generic collection term '{term}' with Ibn Majah 4252 must return False",
            )
            self.assertFalse(
                verify_citation("Hadith", term, 3561),
                f"Generic collection term '{term}' with Abu Dawud 3561 must return False",
            )

    def test_canonical_collections_verified(self):
        """Canonical collections with authentic numbers must return True."""
        canonical_cases = [
            ("Sahih al-Bukhari", 2449),
            ("Sahih al-Bukhari", "2449"),
            ("al-Bukhari", 2449),
            ("Bukhari", 2449),
            ("Sahih Muslim", 2581),
            ("Muslim", 2581),
            ("Sunan Ibn Majah", 4252),
            ("Ibn Majah", 4252),
            ("Sunan Abi Dawud", 3561),
            ("Abu Dawud", 3561),
            ("Abu Dawood", 3561),
        ]
        for coll, num in canonical_cases:
            self.assertTrue(
                verify_citation("Hadith", coll, num),
                f"Canonical citation ({coll}, {num}) must return True",
            )

    def test_hadith_negative_number_rejection(self):
        """
        Negative hadith numbers (e.g. -2449 or '-2449') must be rejected.
        Hyphen stripping in normalize_text must not turn negative numbers into valid numbers.
        """
        self.assertFalse(
            verify_citation("Hadith", "Sahih al-Bukhari", -2449),
            "Negative integer -2449 must return False",
        )
        self.assertFalse(
            verify_citation("Hadith", "Sahih al-Bukhari", "-2449"),
            "Negative string '-2449' must return False",
        )
        self.assertFalse(
            verify_citation("Hadith", "Sahih Muslim", -2581),
            "Negative integer -2581 must return False",
        )

    def test_hadith_non_numeric_and_malformed_numbers(self):
        """Malformed, non-numeric, or corrupted hadith numbers must be rejected."""
        malformed_numbers = [
            "2449-fake",
            "2449/1",
            "2449a",
            "abc",
            None,
            "",
            "   ",
            [],
            {},
            999999,
            0,
            2449.5,
        ]
        for num in malformed_numbers:
            self.assertFalse(
                verify_citation("Hadith", "Sahih al-Bukhari", num),
                f"Malformed hadith number {num!r} must return False",
            )

    def test_hadith_collection_type_confusion(self):
        """Non-string or None collection names must return False without crashing."""
        invalid_colls = [None, 12345, [], {}, True, False, 3.14]
        for coll in invalid_colls:
            self.assertFalse(
                verify_citation("Hadith", coll, 2449),
                f"Invalid collection type {coll!r} must return False without crashing",
            )


class TestFabricatedDuaAdversarialStress(unittest.TestCase):
    """
    Stress tests on Dua verification and anti-hallucination sanitization.
    Tests whether fabricated duas can trick the matcher or bypass sanitization.
    """

    def setUp(self):
        self.rag = get_rag_service()

    def test_canonical_duas_verified(self):
        """All authentic duas in duas.json must be verified."""
        for dua in self.rag._duas_data:
            match = self.rag.verify_dua({"title": dua["title"]})
            self.assertIsNotNone(
                match,
                f"Canonical dua title '{dua['title']}' must be verified",
            )
            # Also verify by ID
            match_id = self.rag.verify_dua({"title": dua["id"]})
            self.assertIsNotNone(
                match_id,
                f"Canonical dua ID '{dua['id']}' must be verified",
            )
            # Also verify by authentic Arabic text
            match_ar = self.rag.verify_dua({"arabic_text": dua["arabic_text"]})
            self.assertIsNotNone(
                match_ar,
                f"Canonical dua Arabic text for '{dua['title']}' must be verified",
            )

    def test_fabricated_duas_with_isolated_alias_words_rejected(self):
        """
        Adversarial test: Fabricated Duas using isolated generic words or alias substrings
        (e.g. 'istighfar', 'yunus', 'adam', 'foraeldre', 'bagtalelse')
        must NOT match canonical duas.
        """
        adversarial_fake_duas = [
            {"title": "Fabricated Istighfar of Shaitan"},
            {"title": "Sayyid Qutb political reflection"},
            {"title": "Muhammad Yunus microfinance dua"},
            {"title": "Adam Smith capitalist prayer"},
            {"title": "Nafs al-Hawa temptation poem"},
            {"title": "Dua mod vrede foraeldre og nabokrig"},
            {"title": "Opdigtet bon om bagtalelse af chefen"},
            {"title": "tilgivelse"},
            {"title": "mestrene"},
            {"title": "alle bonner"},
        ]
        for fake in adversarial_fake_duas:
            match = self.rag.verify_dua(fake)
            self.assertIsNone(
                match,
                f"Adversarial fake dua '{fake['title']}' was incorrectly matched to '{match.get('id') if match else None}'!",
            )

    def test_fabricated_dua_in_sanitizer_preserves_fake_content(self):
        """
        Adversarial test: Test whether validate_and_sanitize_analysis appends
        untrusted dictionary payloads directly, preserving fake Arabic text and translations.
        """
        fake_dua = {
            "title": "Sayyid al-Istighfar",
            "arabic_text": "اللهم اغفر لي بالباطل والبدع المحدثة",
            "transliteration": "Fake transliteration",
            "danish_translation": "Herre tilgiv mig med opdigtet tekst",
            "source": "Fabricated website",
            "context": "Fake context",
        }
        res = self.rag.validate_and_sanitize_analysis({"recommended_duas": [fake_dua]})
        output_duas = res.get("recommended_duas", [])
        self.assertGreaterEqual(len(output_duas), 1)
        output_dua = output_duas[0]

        # The sanitized output must NOT retain fabricated Arabic text or fake translations!
        self.assertNotEqual(
            output_dua.get("arabic_text"),
            "اللهم اغفر لي بالباطل والبدع المحدثة",
            "Sanitizer retained fabricated Arabic text in validated output!",
        )
        self.assertNotEqual(
            output_dua.get("danish_translation"),
            "Herre tilgiv mig med opdigtet tekst",
            "Sanitizer retained fabricated Danish translation in validated output!",
        )

    def test_completely_fabricated_dua_stripped_and_replaced(self):
        """Completely fabricated duas with no canonical relation must be replaced."""
        fake_payload = {
            "recommended_duas": [
                {
                    "title": "Bøn om rigdom og lotterigevinst",
                    "arabic_text": "اللهم ارزقني أموالا بلا حساب من القمار",
                    "transliteration": "Fake",
                    "danish_translation": "Giv mig lotterigevinst",
                    "source": "Internet forum",
                    "context": "Gambling",
                }
            ]
        }
        sanitized = self.rag.validate_and_sanitize_analysis(fake_payload)
        out_titles = [d["title"] for d in sanitized["recommended_duas"]]
        self.assertNotIn(
            "Bøn om rigdom og lotterigevinst",
            out_titles,
            "Completely fabricated dua was not stripped by sanitizer!",
        )


class TestQuranCitationAdversarialStress(unittest.TestCase):
    """Stress tests on Quran citation verification."""

    def setUp(self):
        self.rag = get_rag_service()

    def test_quran_negative_ayah_rejected(self):
        """Negative ayah numbers must be rejected."""
        self.assertFalse(verify_citation("Quran", "Al-Isra", -23))
        self.assertFalse(verify_citation("Quran", "Al-Isra", "-23"))
        self.assertFalse(verify_citation("Quran", "Az-Zumar", -53))

    def test_quran_out_of_bounds_ayah_rejected(self):
        """Ayahs beyond surah length or not in curated dataset must be rejected."""
        self.assertFalse(verify_citation("Quran", "Al-Isra", 0))
        self.assertFalse(verify_citation("Quran", "Al-Isra", 999))
        self.assertFalse(verify_citation("Quran", "Az-Zumar", 150))
        self.assertFalse(verify_citation("Quran", "An-Nisa", 500))

    def test_quran_ayah_type_confusion(self):
        """Non-numeric ayah arguments must return False without crashing."""
        for bad_ayah in [None, "twenty-three", [23], {"ayah": 23}, 23.5]:
            self.assertFalse(
                verify_citation("Quran", "Al-Isra", bad_ayah),
                f"Bad ayah argument {bad_ayah!r} must return False",
            )

    def test_quran_surah_type_confusion(self):
        """Non-string or empty surah arguments must return False without crashing."""
        for bad_surah in [None, "", "   ", 17, [], {}]:
            self.assertFalse(
                verify_citation("Quran", bad_surah, 23),
                f"Bad surah argument {bad_surah!r} must return False",
            )


class TestUniversalCitationAndSanitizationEdgeCases(unittest.TestCase):
    """Stress tests on universal citation dispatcher and sanitizer robustness."""

    def setUp(self):
        self.rag = get_rag_service()

    def test_verify_citation_none_source_type_does_not_crash(self):
        """Passing None or non-string source_type to verify_citation must return False."""
        self.assertFalse(
            verify_citation(None, "Bukhari", 2449),
            "verify_citation(None, ...) must return False instead of raising AttributeError",
        )
        self.assertFalse(
            verify_citation(123, "Bukhari", 2449),
            "verify_citation(123, ...) must return False",
        )
        self.assertFalse(
            verify_citation("", "Bukhari", 2449),
            "verify_citation('', ...) must return False",
        )

    def test_sanitizer_with_null_and_malformed_analysis_payload(self):
        """validate_and_sanitize_analysis must handle null fields and empty dicts."""
        # 1. Null references
        payload_with_nulls = {
            "incident_summary": "Test",
            "quran_references": None,
            "hadith_references": None,
            "recommended_duas": None,
        }
        sanitized = self.rag.validate_and_sanitize_analysis(payload_with_nulls)
        self.assertIsInstance(sanitized["quran_references"], list)
        self.assertIsInstance(sanitized["hadith_references"], list)
        self.assertIsInstance(sanitized["recommended_duas"], list)

        # 2. Corrupted items inside lists
        payload_with_bad_items = {
            "quran_references": [None, {}, {"surah": None, "ayah": None}],
            "hadith_references": [None, {}, {"collection": None, "hadith_number": None}],
            "recommended_duas": [None, {}, {"title": None, "arabic_text": None}],
        }
        sanitized_bad = self.rag.validate_and_sanitize_analysis(payload_with_bad_items)
        self.assertGreaterEqual(len(sanitized_bad["quran_references"]), 1)
        self.assertGreaterEqual(len(sanitized_bad["hadith_references"]), 1)
        self.assertGreaterEqual(len(sanitized_bad["recommended_duas"]), 1)

    def test_extreme_length_and_injection_payloads(self):
        """Long strings and injection payloads must not cause crashes or regex catastrophic backtracking."""
        huge_str = "بِسْمِ اللَّهِ " * 2000  # ~30,000 chars
        sql_injection = "'; DROP TABLE users; SELECT * FROM confessions WHERE '1'='1"
        xss_payload = "<script>alert('xss')</script><img src=x onerror=alert(1)>"

        # Search methods
        q_res = self.rag.search_quran(query=huge_str)
        self.assertIsInstance(q_res, list)
        h_res = self.rag.search_hadith(query=sql_injection)
        self.assertIsInstance(h_res, list)
        d_res = self.rag.search_duas(query=xss_payload)
        self.assertIsInstance(d_res, list)

        # Citation verification
        self.assertFalse(verify_citation("Hadith", sql_injection, 2449))
        self.assertFalse(verify_citation("Quran", xss_payload, 1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
