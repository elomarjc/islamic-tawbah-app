"""
tests/test_challenger2_m2_rechallenge.py

Milestone 2 Challenger 2 Adversarial Re-Challenge & Fiqh Boundary Stress Test Suite:
1. Hostile collection names rejection ('Non-Muslim', 'Anti-Bukhari', 'Fake Bukhari', 'Devil Bukhari', '\u202eSahih al-Bukhari\u202c')
2. Anti-hallucination sanitizer overwrite against canonical quran.json and hadith.json
3. Partial citation dictionary schema enrichment (preventing Pydantic ValidationError)
4. Category type safety (non-string category=123, None, list, dict)
5. Classical Fiqh boundary stress (Al-Sitr, Fitnah avoidance, Anonymous Restitution, Scholar consultation)
6. FastAPI confession intake edge cases and multi-incident consistency
"""

import sys
import unittest
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app
from app.engine.rag_service import (
    IslamicRAGService,
    get_rag_service,
    verify_citation,
    normalize_text,
    normalize_arabic,
    resolve_hadith_collection_family,
)
from app.engine.classifier import (
    classify_rights,
    check_scholar_consultation_required,
    extract_affected_parties,
)
from app.engine.incident_splitter import split_confession_incidents
from app.engine.analyzer import analyze_confession, get_analyzer
from app.schemas import AnalysisResultSchema


class TestMilestone2Rechallenge(unittest.TestCase):
    """Empirical re-challenge harness for Challenger 2."""

    def setUp(self):
        self.rag = get_rag_service()
        self.client = TestClient(app)

    # ------------------------------------------------------------------------
    # 1. Hostile Collection Names Re-Challenge
    # ------------------------------------------------------------------------
    def test_rechallenge_hostile_collection_names(self):
        """
        Verify that hostile collection names:
        'Non-Muslim', 'Anti-Bukhari', 'Fake Bukhari', 'Devil Bukhari', '\u202eSahih al-Bukhari\u202c'
        are all rejected (verify_citation returns False).
        """
        mandatory_hostile = [
            ("Non-Muslim", 2581),
            ("Anti-Bukhari", 2449),
            ("Fake Bukhari", 2449),
            ("Devil Bukhari", 2449),
            ("\u202eSahih al-Bukhari\u202c", 2449),
        ]
        for coll, num in mandatory_hostile:
            result = verify_citation("Hadith", coll, num)
            self.assertFalse(
                result,
                f"VULNERABILITY: Hostile collection {coll!r} with Hadith {num} returned True!",
            )

        # Extended hostile variants
        extended_hostile = [
            ("Pseudo-Muslim", 2581),
            ("Not-Bukhari", 2449),
            ("Anti-Muslim", 2581),
            ("Ex-Muslim", 2581),
            ("Fake Abu Dawud", 3561),
            ("Pseudo Ibn Majah", 4252),
            ("\u202eMuslim\u202c", 2581),
            ("Devil Muslim", 2581),
        ]
        for coll, num in extended_hostile:
            self.assertFalse(
                verify_citation("Hadith", coll, num),
                f"VULNERABILITY: Extended hostile collection {coll!r} returned True!",
            )

    # ------------------------------------------------------------------------
    # 2. Anti-Hallucination Sanitizer Overwrite
    # ------------------------------------------------------------------------
    def test_rechallenge_anti_hallucination_sanitizer_overwrite(self):
        """
        Fabricated Arabic or Danish text passed into validate_and_sanitize_analysis
        must be overwritten with authentic canonical text from quran.json and hadith.json.
        """
        canon_q = self.rag.get_canonical_quran("Az-Zumar", 53)
        self.assertIsNotNone(canon_q, "Canonical Quran 39:53 must exist in dataset")

        canon_h = self.rag.get_canonical_hadith("Sahih al-Bukhari", 2449)
        self.assertIsNotNone(canon_h, "Canonical Bukhari 2449 must exist in dataset")

        fabricated_payload = {
            "quran_references": [
                {
                    "surah": "Az-Zumar",
                    "ayah": 53,
                    "arabic_text": "قُلْ هَذَا كَلَامٌ مُفْتَرًى وَلَيْسَ مِنَ الْقُرْآنِ",
                    "danish_translation": "Falsk opdigtet dansk oversaettelse af Az-Zumar 53",
                    "explanation": "Valid context explanation",
                }
            ],
            "hadith_references": [
                {
                    "collection": "Sahih al-Bukhari",
                    "hadith_number": "2449",
                    "arabic_text": "هَذَا حَدِيثٌ مَكْذُوبٌ وَمَوْضُوعٌ",
                    "danish_translation": "Falsk opdigtet dansk oversaettelse af Bukhari 2449",
                    "explanation": "Valid context explanation",
                }
            ],
        }

        sanitized = self.rag.validate_and_sanitize_analysis(fabricated_payload)
        out_q = sanitized["quran_references"][0]
        out_h = sanitized["hadith_references"][0]

        # Arabic text must be overwritten with canonical Arabic
        self.assertEqual(
            out_q["arabic_text"],
            canon_q["arabic_text"],
            "VULNERABILITY: Fabricated Quran Arabic was not overwritten with canonical text!",
        )
        # Danish translation must be overwritten with canonical translation
        self.assertEqual(
            out_q["danish_translation"],
            canon_q["danish_translation"],
            "VULNERABILITY: Fabricated Quran Danish translation was not overwritten!",
        )
        # Hadith Arabic must be overwritten
        self.assertEqual(
            out_h["arabic_text"],
            canon_h["arabic_text"],
            "VULNERABILITY: Fabricated Hadith Arabic was not overwritten with canonical text!",
        )
        # Hadith Danish must be overwritten
        self.assertEqual(
            out_h["danish_translation"],
            canon_h["danish_translation"],
            "VULNERABILITY: Fabricated Hadith Danish translation was not overwritten!",
        )

    # ------------------------------------------------------------------------
    # 3. Partial Citation Dictionary Schema Enrichment
    # ------------------------------------------------------------------------
    def test_rechallenge_partial_citation_dictionary_schema_enrichment(self):
        """
        Minimal citation dicts (e.g. {'surah': 'Az-Zumar', 'ayah': 53})
        must have required fields automatically enriched so AnalysisResultSchema.model_validate()
        never crashes with ValidationError.
        """
        minimal_payload = {
            "incident_summary": "Minimal schema stress test",
            "incidents": [],
            "sin_classification": "huqooq_allah",
            "allah_rights": ["Ret til tilbedelse"],
            "people_rights": [],
            "affected_parties": ["Allah"],
            "severity_explanation": "Test af skemaopfyldelse",
            "required_actions": [],
            "recommended_actions": [],
            "quran_references": [{"surah": "Az-Zumar", "ayah": 53}],
            "hadith_references": [{"collection": "Sahih al-Bukhari", "hadith_number": "2449"}],
            "recommended_duas": [{"title": "Sayyid al-Istighfar"}],
            "confidence_level": "high",
            "scholar_consultation_required": False,
            "final_reminder": "Husk Allahs uendelige barmhjertighed",
        }

        sanitized = self.rag.validate_and_sanitize_analysis(minimal_payload)

        # Must strictly validate with Pydantic without ValidationError
        try:
            validated = AnalysisResultSchema.model_validate(sanitized)
        except Exception as e:
            self.fail(f"VULNERABILITY: Minimal citation dictionary crashed AnalysisResultSchema: {e}")

        # Verify all required fields are present and non-empty
        q_ref = validated.quran_references[0]
        self.assertTrue(bool(q_ref.arabic_text))
        self.assertTrue(bool(q_ref.danish_translation))
        self.assertTrue(bool(q_ref.explanation))

        h_ref = validated.hadith_references[0]
        self.assertTrue(bool(h_ref.authenticity_grading))
        self.assertTrue(bool(h_ref.arabic_text))
        self.assertTrue(bool(h_ref.danish_translation))
        self.assertTrue(bool(h_ref.explanation))

        d_ref = validated.recommended_duas[0]
        self.assertTrue(bool(d_ref.arabic_text))
        self.assertTrue(bool(d_ref.transliteration))
        self.assertTrue(bool(d_ref.danish_translation))
        self.assertTrue(bool(d_ref.source))
        self.assertTrue(bool(d_ref.context))

    # ------------------------------------------------------------------------
    # 4. Category Type Safety
    # ------------------------------------------------------------------------
    def test_rechallenge_category_type_safety(self):
        """
        Non-string category arguments (category=123, None, list, dict)
        must be handled safely without AttributeError.
        """
        test_inputs = [
            123,
            None,
            ["tawbah"],
            {"category": "tawbah"},
            True,
            False,
            3.14159,
            object(),
        ]
        for bad_cat in test_inputs:
            try:
                res_q = self.rag.search_quran(category=bad_cat)
                self.assertIsInstance(res_q, list)

                res_h = self.rag.search_hadith(category=bad_cat)
                self.assertIsInstance(res_h, list)

                res_d = self.rag.search_duas(category=bad_cat)
                self.assertIsInstance(res_d, list)

                ev = self.rag.get_evidence_for_scenario(bad_cat)
                self.assertIsInstance(ev, dict)
                self.assertIn("quran", ev)
                self.assertIn("hadith", ev)
                self.assertIn("duas", ev)
                self.assertIn("fiqh_rules", ev)
            except AttributeError as ae:
                self.fail(f"VULNERABILITY: Category argument {bad_cat!r} raised AttributeError: {ae}")
            except Exception as e:
                self.fail(f"VULNERABILITY: Category argument {bad_cat!r} raised unhandled exception: {e}")

    # ------------------------------------------------------------------------
    # 5. Fiqh Boundary Stress
    # ------------------------------------------------------------------------
    def test_fiqh_boundary_al_sitr_concealment(self):
        """
        Al-Sitr (Concealment of private sins):
        When a sin is purely between the servant and Allah in secret,
        public exposure/confession is strictly prohibited in Sunni fiqh.
        Classification MUST be huqooq_allah, affected_parties MUST be [],
        and guidance must enforce concealment.
        """
        private_confession = "Jeg begik en hemmelig synd alene i mit værelse foran skærmen som kun Allah kender til."
        analysis = analyze_confession(private_confession)

        self.assertEqual(
            analysis["sin_classification"],
            "huqooq_allah",
            "Private sin must be classified as huqooq_allah",
        )
        self.assertEqual(
            analysis["affected_parties"],
            [],
            "Pure huqooq_allah must have zero affected parties",
        )
        self.assertEqual(
            analysis["people_rights"],
            [],
            "Pure huqooq_allah must have zero people rights",
        )

        all_text = " ".join([
            analysis.get("apology_guidance", "") or "",
            analysis.get("severity_explanation", "") or "",
            " ".join(a["description"] for a in analysis["required_actions"]),
        ]).lower()
        self.assertTrue(
            any(w in all_text for w in ["hemmelig", "skjul", "sitr", "fortæl ikke", "ikke offentliggør"]),
            "Fiqh guidance must advise concealment (Al-Sitr) for private sins",
        )

    def test_fiqh_boundary_fitnah_avoidance_in_backbiting(self):
        """
        Backbiting (Gheebah) with fitnah nuance:
        If the victim does not know and informing them would cause hatred/fitnah,
        Sunni scholars (Ibn Taymiyyah, Ibn al-Qayyim) rule that direct disclosure
        is waived and replaced by dua, istighfar, and praise.
        """
        backbiting_confession = "Jeg kom til at bagtale min kollega foran andre til frokost. Han ved det ikke endnu."
        analysis = analyze_confession(backbiting_confession)

        self.assertEqual(analysis["sin_classification"], "both")
        self.assertIn("Kollegaen", analysis["affected_parties"])

        # Check scholarly disagreement or apology guidance discloses the fitnah nuance
        combined_guidance = (
            (analysis.get("apology_guidance") or "") + " " +
            (analysis.get("scholarly_disagreement") or "")
        ).lower()
        self.assertTrue(
            any(k in combined_guidance for k in ["fitnah", "splid", "dua", "forbøn", "hvis personen ikke ved"]),
            "Backbiting analysis must disclose fitnah avoidance nuance",
        )

    def test_fiqh_boundary_anonymous_restitution(self):
        """
        Anonymous restitution (Radd al-Mazalim):
        Stealing property/money requires return, but permits secret/anonymous return
        if direct confession would cause severe fitnah or destruction of family.
        """
        theft_confession = "Jeg stjal 5000 kr fra butikken for mange år siden. Jeg vil tilbagelevere pengene anonymt."
        analysis = analyze_confession(theft_confession)

        self.assertEqual(analysis["sin_classification"], "both")
        restitution_text = (analysis.get("restitution_guidance") or "").lower()
        self.assertTrue(
            any(k in restitution_text for k in ["anonym", "hemmeligt", "bankoverførsel", "uden at afsløre"]),
            "Restitution guidance must permit anonymous return to protect the repenting person",
        )

    def test_fiqh_boundary_scholar_consultation_trigger(self):
        """
        Violence, physical abuse, or severe crimes MUST trigger scholar_consultation_required=True.
        Ordinary non-violent sins must NOT trigger it.
        """
        violent_confession = "Jeg blev så vred under et skænderi at jeg slog min kone og brugte fysisk vold."
        analysis_violent = analyze_confession(violent_confession)
        self.assertTrue(
            analysis_violent["scholar_consultation_required"],
            "Physical violence MUST trigger scholar_consultation_required=True",
        )

        nonviolent_confession = "Jeg sov over mig og missede Fajr-bønnen i morges."
        analysis_nonviolent = analyze_confession(nonviolent_confession)
        self.assertFalse(
            analysis_nonviolent["scholar_consultation_required"],
            "Non-violent missed prayer should not trigger scholar consultation",
        )

    # ------------------------------------------------------------------------
    # 6. FastAPI Confession Intake Stress
    # ------------------------------------------------------------------------
    def test_fastapi_confession_intake_stress(self):
        """
        FastAPI intake endpoint /api/confessions/text:
        - Rejects missing consent (400)
        - Rejects empty/whitespace text (400)
        - Handles Danish characters (æ, ø, å) perfectly
        - Returns 200 with schema compliance
        """
        # 1. Missing consent
        res_no_consent = self.client.post(
            "/api/confessions/text",
            json={"text": "Jeg gjorde noget forkert.", "consent": False},
        )
        self.assertEqual(res_no_consent.status_code, 400)

        # 2. Empty text
        res_empty = self.client.post(
            "/api/confessions/text",
            json={"text": "   ", "consent": True},
        )
        self.assertEqual(res_empty.status_code, 400)

        # 3. Danish characters
        danish_text = "Jeg råbte ad min kære mor og fortryder det bittert. Åh Allah, tilgiv mig."
        res_danish = self.client.post(
            "/api/confessions/text",
            json={"text": danish_text, "consent": True},
        )
        self.assertEqual(res_danish.status_code, 200)
        data = res_danish.json()
        self.assertEqual(data["sin_classification"], "both")
        self.assertTrue(any("mor" in p.lower() for p in data["affected_parties"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
