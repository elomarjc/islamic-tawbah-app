"""
tests/stress_m1_rag_schema.py

Adversarial Stress Test Suite for Milestone 1:
- RAG Retrieval & Inverted Indexing
- Fabricated Citation Rejection & Anti-Hallucination Sanitization
- Danish Diacritics (æ, ø, å) & Keyword Search Edge Cases
- All 10 Required Confession Scenarios Retrieval Verification
- Pydantic v2 Schema Boundary & Malicious Payload Hardening
"""

import os
import sys
import json
import unittest
from pathlib import Path
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.rag_service import (
    IslamicRAGService,
    get_rag_service,
    verify_citation,
    normalize_text,
)
from app.schemas import (
    AnalysisResultSchema,
    IncidentSchema,
    ActionItemSchema,
    QuranReference,
    HadithReference,
    RecommendedDua,
    TextConfessionRequest,
    UserRegisterRequest,
    UserLoginRequest,
)


class TestFabricatedCitationRejection(unittest.TestCase):
    """
    Stress-tests Requirement R3: Strict anti-hallucination citation rejection.
    Every fabricated verse, hadith number, or non-authentic collection must be rejected.
    """

    def setUp(self):
        self.rag = get_rag_service()

    def test_fabricated_quran_surahs_rejected(self):
        """Fabricated surah names must be rejected."""
        fake_surahs = [
            "FakeSurah",
            "Al-Ikhtira",
            "Surah 999",
            "Gospel of Barnabas",
            "Book of Mormon",
            "",
            "   ",
            "115",  # Quran has 114 surahs
            "Surah 115",
        ]
        for surah in fake_surahs:
            self.assertFalse(
                self.rag.verify_quran_citation(surah, 1),
                f"Fabricated surah '{surah}' was incorrectly accepted!"
            )

    def test_fabricated_quran_ayahs_rejected(self):
        """Genuine surahs with non-existent ayah numbers must be rejected."""
        # Al-Isra has 111 ayahs, Al-Baqarah has 286 ayahs
        fake_citations = [
            ("Al-Isra", 112),
            ("Al-Isra", 999),
            ("Al-Baqarah", 287),
            ("Al-Baqarah", 9999),
            ("Az-Zumar", 150),
            ("An-Nisa", 500),
            ("Maryam", 200),
            ("Al-Isra", 0),
            ("Al-Isra", -1),
            ("Al-Isra", "not_a_number"),
            ("Al-Isra", "23-24"),  # Range string
            ("Al-Isra", None),
        ]
        for surah, ayah in fake_citations:
            self.assertFalse(
                self.rag.verify_quran_citation(surah, ayah),
                f"Quran citation ({surah}, {ayah}) was incorrectly accepted!"
            )

    def test_canonical_quran_citations_accepted(self):
        """All genuine verses in quran.json must be accepted."""
        for item in self.rag._quran_data:
            surah = item["surah"]
            ayah = item["ayah"]
            self.assertTrue(
                self.rag.verify_quran_citation(surah, ayah),
                f"Canonical Quran citation ({surah}, {ayah}) was rejected!"
            )

    def test_quran_sun_letter_prefix_normalization_edge_cases(self):
        """
        Adversarial test on Arabic sun-letter prefix stripping:
        Tests whether 'Az-Zumar' matches 'Zumar', 'An-Nisa' matches 'Nisa', etc.
        """
        # Az-Zumar 53 exists in dataset
        has_azzumar = self.rag.verify_quran_citation("Az-Zumar", 53)
        has_zumar = self.rag.verify_quran_citation("Zumar", 53)
        # An-Nisa 110 exists in dataset
        has_annisa = self.rag.verify_quran_citation("An-Nisa", 110)
        has_nisa = self.rag.verify_quran_citation("Nisa", 110)
        # Al-Isra 23 exists in dataset
        has_alisra = self.rag.verify_quran_citation("Al-Isra", 23)
        has_isra = self.rag.verify_quran_citation("Isra", 23)

        self.assertTrue(has_azzumar, "Canonical Az-Zumar 53 must verify")
        self.assertTrue(has_annisa, "Canonical An-Nisa 110 must verify")
        self.assertTrue(has_alisra, "Canonical Al-Isra 23 must verify")
        self.assertTrue(has_isra, "Al- prefix stripped Isra 23 must verify")

        # Document whether Sun-letter prefixes (Az-, An-) are stripped:
        print(f"\n[STRESS TEST] Sun-letter prefix stripping: 'Zumar 53' verified: {has_zumar}, 'Nisa 110' verified: {has_nisa}")

    def test_fabricated_hadith_collections_rejected(self):
        """Fabricated collection names must be rejected."""
        fake_colls = [
            "FakeHadithCollection",
            "Kitab al-Majhul",
            "Shakespeare",
            "Al-Kafi",
            "Bihar al-Anwar",
            "Unknown",
            "",
            "   ",
        ]
        for coll in fake_colls:
            self.assertFalse(
                self.rag.verify_hadith_citation(coll, 2449),
                f"Fabricated hadith collection '{coll}' was incorrectly accepted!"
            )

    def test_fabricated_hadith_numbers_rejected(self):
        """Genuine collections with non-existent hadith numbers must be rejected."""
        fake_hadiths = [
            ("Sahih al-Bukhari", "99999"),
            ("Sahih al-Bukhari", "0"),
            ("Sahih al-Bukhari", "-5"),
            ("Sahih al-Bukhari", "random_string"),
            ("Sahih Muslim", "99999"),
            ("Sunan Ibn Majah", "88888"),
            ("Sunan Abi Dawud", "77777"),
            ("Sahih al-Bukhari", ""),
            ("Sahih al-Bukhari", None),
        ]
        for coll, num in fake_hadiths:
            self.assertFalse(
                self.rag.verify_hadith_citation(coll, num),
                f"Fabricated hadith citation ({coll}, {num}) was incorrectly accepted!"
            )

    def test_canonical_hadith_citations_accepted(self):
        """All genuine hadiths in hadith.json must be accepted."""
        for item in self.rag._hadith_data:
            coll = item["collection"]
            num = item["hadith_number"]
            self.assertTrue(
                self.rag.verify_hadith_citation(coll, num),
                f"Canonical Hadith citation ({coll}, {num}) was rejected!"
            )

    def test_hadith_substring_matching_vulnerability(self):
        """
        Adversarial test: Substring matching in verify_hadith_citation:
        '(known_coll in norm_coll or norm_coll in known_coll)'.
        Tests whether single letters or generic words match known hadiths.
        """
        # Single letters that are substrings of 'bukhari', 'muslim', etc.
        vulnerable_inputs = ["a", "s", "i", "b", "sahih"]
        leak_results = {}
        for coll in vulnerable_inputs:
            # 2449 is a valid Bukhari hadith
            matched = self.rag.verify_hadith_citation(coll, 2449)
            leak_results[coll] = matched

        print(f"\n[STRESS TEST] Hadith collection substring vulnerability leak results: {leak_results}")
        # Note: 'sahih' matches Bukhari 2449 because 'sahih' is in 'sahih al-bukhari'

    def test_anti_hallucination_sanitizer_replaces_fake_citations(self):
        """validate_and_sanitize_analysis must strip fabricated Quran and Hadith references."""
        hallucinated_analysis = {
            "incident_summary": "Test summary",
            "quran_references": [
                {
                    "surah": "FakeSurah",
                    "ayah": 8888,
                    "arabic_text": "Fake Arabic",
                    "danish_translation": "Fake Danish",
                    "explanation": "Fake explanation",
                }
            ],
            "hadith_references": [
                {
                    "collection": "FakeCollection",
                    "hadith_number": "99999",
                    "authenticity_grading": "Mawdu (Fabricated)",
                    "arabic_text": None,
                    "danish_translation": "Fake Hadith",
                    "explanation": "Fake Sharh",
                }
            ],
            "recommended_duas": [],
        }

        sanitized = self.rag.validate_and_sanitize_analysis(hallucinated_analysis)

        # Quran references must NOT contain FakeSurah
        q_surahs = [q["surah"] for q in sanitized["quran_references"]]
        self.assertNotIn("FakeSurah", q_surahs, "Sanitizer failed to strip FakeSurah!")
        self.assertGreaterEqual(len(sanitized["quran_references"]), 1, "Sanitizer must supply verified fallback")

        # Hadith references must NOT contain FakeCollection
        h_colls = [h["collection"] for h in sanitized["hadith_references"]]
        self.assertNotIn("FakeCollection", h_colls, "Sanitizer failed to strip FakeCollection!")
        self.assertGreaterEqual(len(sanitized["hadith_references"]), 1, "Sanitizer must supply verified fallback")

    def test_anti_hallucination_sanitizer_dua_bypass(self):
        """
        Adversarial test: Test whether validate_and_sanitize_analysis
        allows completely fabricated Duas through via 'if matched or d.get("arabic_text"):'.
        """
        fake_dua_payload = {
            "quran_references": [],
            "hadith_references": [],
            "recommended_duas": [
                {
                    "title": "Completely Fabricated Apocryphal Dua",
                    "arabic_text": "FABRICATED ARABIC TEXT",
                    "transliteration": "Fake transliteration",
                    "danish_translation": "Fake translation",
                    "source": "Fabricated source",
                    "context": "Fake context",
                }
            ],
        }

        sanitized = self.rag.validate_and_sanitize_analysis(fake_dua_payload)
        titles = [d["title"] for d in sanitized["recommended_duas"]]
        dua_leaked = "Completely Fabricated Apocryphal Dua" in titles
        print(f"\n[STRESS TEST] Fabricated Dua bypassed anti-hallucination filter: {dua_leaked}")


class TestDanishSearchAndDiacritics(unittest.TestCase):
    """
    Stress-tests search indexing, Danish diacritics (æ, ø, å),
    and hyphenated transliteration edge cases.
    """

    def setUp(self):
        self.rag = get_rag_service()

    def test_danish_diacritics_queries(self):
        """Queries containing Danish æ, ø, å must retrieve relevant records."""
        test_queries = [
            ("forældre", "quran", 1),    # Al-Isra 23/24
            ("bagtalelse", "quran", 1),  # Al-Hujurat 12
            ("bøn", "hadith", 1),        # Salah / prayer
            ("tilgivelse", "quran", 1),  # Repentance
            ("tyveri", "quran", 1),      # An-Nisa 29
        ]
        for query_str, domain, min_expected in test_queries:
            if domain == "quran":
                res = self.rag.search_quran(query=query_str, limit=3)
            elif domain == "hadith":
                res = self.rag.search_hadith(query=query_str, limit=3)
            self.assertGreaterEqual(
                len(res),
                min_expected,
                f"Query '{query_str}' in {domain} returned insufficient results!"
            )

    def test_hyphenated_search_token_mismatch(self):
        """
        Adversarial test: normalize_text strips hyphens from queries,
        but haystack is not normalized with normalize_text (only .lower()),
        causing queries like 'Al-Isra', 'Az-Zumar', 'al-Bukhari' to fail to match!
        """
        # Surah with hyphen
        res_hyphen_quran = self.rag.search_quran(query="Al-Isra")
        surahs = [r.surah for r in res_hyphen_quran]
        matched_isra = any("isra" in s.lower() for s in surahs)

        # Surah without hyphen in query
        res_clean_quran = self.rag.search_quran(query="isra")
        matched_isra_clean = any("isra" in s.lower() for s in [r.surah for r in res_clean_quran])

        # Hadith with hyphen
        res_hyphen_hadith = self.rag.search_hadith(query="al-Bukhari")
        colls = [h.collection for h in res_hyphen_hadith]
        matched_bukhari = any("bukhari" in c.lower() for c in colls)

        res_clean_hadith = self.rag.search_hadith(query="Bukhari")
        matched_bukhari_clean = any("bukhari" in c.lower() for c in [h.collection for h in res_clean_hadith])

        print(f"\n[STRESS TEST] Hyphen search results:")
        print(f"  'Al-Isra' matched Al-Isra: {matched_isra} (Fallback returned instead: {not matched_isra})")
        print(f"  'isra' matched Al-Isra: {matched_isra_clean}")
        print(f"  'al-Bukhari' matched Bukhari: {matched_bukhari} (Fallback returned instead: {not matched_bukhari})")
        print(f"  'Bukhari' matched Bukhari: {matched_bukhari_clean}")

    def test_danish_verb_inflections(self):
        """
        Tests whether Danish verb forms like 'stjæle' (steal), 'stjal', 'stjålet'
        match stealing verses or trigger fallback.
        """
        res_stjaele = self.rag.search_quran(query="stjæle")
        res_tyveri = self.rag.search_quran(query="tyveri")

        stjaele_nisa = any(r.surah == "An-Nisa" and r.ayah == 29 for r in res_stjaele)
        tyveri_nisa = any(r.surah == "An-Nisa" and r.ayah == 29 for r in res_tyveri)

        print(f"\n[STRESS TEST] Danish verb inflection:")
        print(f"  'stjæle' matched An-Nisa 29: {stjaele_nisa}")
        print(f"  'tyveri' matched An-Nisa 29: {tyveri_nisa}")


class Test10ScenariosEvidenceCoverage(unittest.TestCase):
    """
    Stress-tests Section 13 / Acceptance Criteria R5:
    All 10 required confession scenarios must have appropriate canonical evidence.
    """

    def setUp(self):
        self.rag = get_rag_service()
        self.scenarios = [
            "insulting_mother",
            "stealing_father",
            "backbiting",
            "missing_fajr",
            "lying_to_spouse",
            "damaging_property",
            "returning_taken_money",
            "private_sin",
            "false_accusation",
            "breaking_trust",
        ]

    def test_all_10_scenarios_have_complete_evidence(self):
        """Every scenario must return Quran, Hadith, Duas, and Fiqh rules."""
        for sc in self.scenarios:
            ev = self.rag.get_evidence_for_scenario(sc)
            self.assertGreaterEqual(
                len(ev["quran"]), 1, f"Scenario '{sc}' has no Quran references!"
            )
            self.assertGreaterEqual(
                len(ev["hadith"]), 1, f"Scenario '{sc}' has no Hadith references!"
            )
            self.assertGreaterEqual(
                len(ev["duas"]), 1, f"Scenario '{sc}' has no recommended Duas!"
            )
            self.assertGreaterEqual(
                len(ev["fiqh_rules"]), 1, f"Scenario '{sc}' has no applicable Fiqh rules!"
            )

    def test_scenario_evidence_theological_accuracy(self):
        """Validates specific theological mappings for key scenarios."""
        # 1. Mother insult must retrieve parent verse (Al-Isra 23 or 24)
        mother_ev = self.rag.get_evidence_for_scenario("insulting_mother")
        mother_surahs = [q.surah for q in mother_ev["quran"]]
        self.assertIn("Al-Isra", mother_surahs)

        # 2. Backbiting must retrieve Al-Hujurat 12 and backbiting dua
        backbiting_ev = self.rag.get_evidence_for_scenario("backbiting")
        backbiting_surahs = [q.surah for q in backbiting_ev["quran"]]
        self.assertIn("Al-Hujurat", backbiting_surahs)
        dua_titles = [d.title for d in backbiting_ev["duas"]]
        self.assertTrue(any("Bagtalte" in t for t in dua_titles))

        # 3. Stealing from father must include restitution rule
        steal_ev = self.rag.get_evidence_for_scenario("stealing_father")
        rule_ids = [r["rule_id"] for r in steal_ev["fiqh_rules"]]
        self.assertIn("rule_tawbah_condition_restitution", rule_ids)
        self.assertIn("rule_anonymous_restitution", rule_ids)

        # 4. Missing Fajr must include scholarly disagreement rule on missed prayers
        fajr_ev = self.rag.get_evidence_for_scenario("missing_fajr")
        fajr_rules = [r["rule_id"] for r in fajr_ev["fiqh_rules"]]
        self.assertIn("rule_scholarly_disagreement_missed_prayers", fajr_rules)

        # 5. Private sin must include concealment (Sitr) rule
        private_ev = self.rag.get_evidence_for_scenario("private_sin")
        private_rules = [r["rule_id"] for r in private_ev["fiqh_rules"]]
        self.assertIn("rule_concealment_sitr", private_rules)


class TestPydanticSchemaBoundaries(unittest.TestCase):
    """
    Stress-tests Pydantic v2 schemas:
    Boundaries, extreme payloads, Unicode, injection, missing keys, and strict typing.
    """

    def _get_valid_analysis_payload(self):
        return {
            "incident_summary": "Test sammanfatning",
            "incidents": [
                {
                    "incident_id": "inc-001",
                    "incident_title": "Bagtalelse af kollega",
                    "sin_classification": "huqooq_al_ibad",
                    "description": "Bagtalelse på arbejdspladsen",
                    "affected_parties": ["Kollega"],
                    "allah_rights": ["Lydighed mod forbud"],
                    "people_rights": ["Ære og omdømme"],
                    "required_actions": [
                        {
                            "id": "act-001",
                            "category": "wajib",
                            "description": "Stop bagtalelse øjeblikkeligt",
                            "explanation": "Iqla er en obligatorisk betingelse",
                            "target_party": "Allah",
                            "completed": False,
                        }
                    ],
                    "recommended_actions": [],
                    "apology_guidance": "Undgå fitnah",
                    "restitution_guidance": None,
                }
            ],
            "sin_classification": "huqooq_al_ibad",
            "allah_rights": ["Lydighed mod forbud"],
            "people_rights": ["Ære og omdømme"],
            "affected_parties": ["Kollega"],
            "severity_explanation": "Alvorlig synd i islam",
            "required_actions": [
                {
                    "id": "act-001",
                    "category": "wajib",
                    "description": "Stop bagtalelse øjeblikkeligt",
                    "explanation": "Iqla er en obligatorisk betingelse",
                    "target_party": "Allah",
                    "completed": False,
                }
            ],
            "recommended_actions": [],
            "apology_guidance": "Undgå fitnah",
            "restitution_guidance": None,
            "quran_references": [
                {
                    "surah": "Al-Hujurat",
                    "ayah": 12,
                    "arabic_text": "يَا أَيُّهَا الَّذِينَ آمَنُوا اجْتَنِبُوا كَثِيرًا مِّنَ الظَّنِّ",
                    "danish_translation": "O I, som tror! Undgå megen mistanke...",
                    "explanation": "Forbud mod bagtalelse",
                }
            ],
            "hadith_references": [
                {
                    "collection": "Sahih Muslim",
                    "hadith_number": "2587",
                    "authenticity_grading": "Sahih (Autentisk)",
                    "arabic_text": "أَتَدْرُونَ مَا الْغِيبَةُ",
                    "danish_translation": "Ved I, hvad bagtalelse er?",
                    "explanation": "Definerer bagtalelse",
                }
            ],
            "recommended_duas": [
                {
                    "title": "Bøn om Tilgivelse for den Bagtalte",
                    "arabic_text": "اللَّهُمَّ اغْفِرْ لَنَا وَلَهُ",
                    "transliteration": "Allahumma-ghfir lana wa lahu",
                    "danish_translation": "O Allah, tilgiv os og ham.",
                    "source": "Klassisk Ahlus-Sunnah praksis",
                    "context": "Når man har bagtalt en person",
                }
            ],
            "scholarly_disagreement": "Forskellig opfattelse af om direkte undskyldning er påkrævet hvis det skaber fitnah",
            "confidence_level": "high",
            "scholar_consultation_required": False,
            "final_reminder": "Allah er den Mest Tilgivende, den Mest Barmhjertige.",
        }

    def test_schema_valid_payload_parsing(self):
        """Complete 17-field valid payload must instantiate successfully."""
        payload = self._get_valid_analysis_payload()
        schema = AnalysisResultSchema(**payload)
        self.assertEqual(schema.sin_classification, "huqooq_al_ibad")
        self.assertEqual(len(schema.incidents), 1)
        self.assertEqual(len(schema.quran_references), 1)

    def test_missing_mandatory_fields_raise_validation_error(self):
        """Mandatory fields must not be omitted."""
        mandatory_fields = [
            "incident_summary",
            "sin_classification",
            "severity_explanation",
            "final_reminder",
        ]
        base_payload = self._get_valid_analysis_payload()
        for field in mandatory_fields:
            corrupted = base_payload.copy()
            del corrupted[field]
            with self.assertRaises(ValidationError, msg=f"Missing field '{field}' should have raised ValidationError"):
                AnalysisResultSchema(**corrupted)

    def test_invalid_literal_enums_rejected(self):
        """sin_classification and confidence_level must adhere strictly to allowed Literals."""
        base_payload = self._get_valid_analysis_payload()

        # Invalid sin_classification
        invalid_classifications = ["unknown", "haram", "makruh", "rights_allah", 123, ""]
        for val in invalid_classifications:
            with self.assertRaises(ValidationError, msg=f"sin_classification='{val}' should be rejected"):
                AnalysisResultSchema(**{**base_payload, "sin_classification": val})

        # Invalid confidence_level
        invalid_confidences = ["very_high", "sure", 1, ""]
        for val in invalid_confidences:
            with self.assertRaises(ValidationError, msg=f"confidence_level='{val}' should be rejected"):
                AnalysisResultSchema(**{**base_payload, "confidence_level": val})

    def test_action_item_invalid_category_rejected(self):
        """ActionItemSchema category must be in ActionCategoryType."""
        with self.assertRaises(ValidationError):
            ActionItemSchema(
                id="act-999",
                category="invalid_category",  # type: ignore
                description="Test description",
            )

    def test_extreme_unicode_arabic_diacritics_and_emojis(self):
        """Schemas must gracefully handle Arabic Uthmani text with full tashkeel, emojis, and Danish chars."""
        base_payload = self._get_valid_analysis_payload()
        base_payload["incident_summary"] = (
            "Test: æ, ø, å, Æ, Ø, Å — "
            "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ 🤲🕌 "
            "\U0001F600\U0001F64F\U0001F4AA "
            "Zero-width joiners: \u200b\u200c\u200d"
        )
        base_payload["final_reminder"] = "قُلْ يَا عِبَادِيَ الَّذِينَ أَسْرَفُوا عَلَىٰ أَنفُسِهِمْ"
        schema = AnalysisResultSchema(**base_payload)
        self.assertIn("بِسْمِ", schema.incident_summary)
        self.assertIn("æ, ø, å", schema.incident_summary)

    def test_oversized_payload_stress(self):
        """Schemas must handle large texts without crashing (100,000 characters)."""
        base_payload = self._get_valid_analysis_payload()
        huge_text = "Dette er en meget lang tekst. " * 3500  # ~105,000 characters
        base_payload["incident_summary"] = huge_text
        schema = AnalysisResultSchema(**base_payload)
        self.assertEqual(len(schema.incident_summary), len(huge_text))

    def test_deeply_nested_incidents_and_actions_stress(self):
        """Schemas must handle 50 incidents each with 10 action items."""
        base_payload = self._get_valid_analysis_payload()
        incidents = []
        for i in range(50):
            actions = [
                ActionItemSchema(
                    id=f"act-{i}-{j}",
                    category="wajib" if j % 2 == 0 else "mustahabb",
                    description=f"Action step {j} for incident {i}",
                    completed=False,
                )
                for j in range(10)
            ]
            inc = IncidentSchema(
                incident_id=f"inc-{i:03d}",
                incident_title=f"Incident title {i}",
                sin_classification="both",
                description=f"Description of compound incident {i}",
                affected_parties=[f"Victim {i}"],
                allah_rights=["Rights of Allah"],
                people_rights=["Rights of People"],
                required_actions=[a for a in actions if a.category == "wajib"],
                recommended_actions=[a for a in actions if a.category == "mustahabb"],
            )
            incidents.append(inc)

        base_payload["incidents"] = [inc.model_dump() for inc in incidents]
        schema = AnalysisResultSchema(**base_payload)
        self.assertEqual(len(schema.incidents), 50)
        self.assertEqual(len(schema.incidents[0].required_actions), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
