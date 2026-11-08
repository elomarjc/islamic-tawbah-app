"""
tests/test_incident_splitter.py

Unit tests for Incident Splitter engine (Feature #8).
Verifies:
- All 10 canonical single-sin scenarios remain unified as 1 incident.
- Compound multi-sin confessions split into discrete atomic incidents.
- Numbered and bulleted lists.
- Discourse transition markers (Derudover, Desuden, etc.).
- Boundary conditions (empty/whitespace).
- Danish characters preservation.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.engine.incident_splitter import (
    split_confession_incidents,
    split_confession_heuristic,
    to_incident_details,
    IncidentSplitter,
    get_incident_splitter,
)
from tests.test_base import TEN_SCENARIOS, tier


class TestIncidentSplitter(unittest.TestCase):
    """Unit tests for the multi-sin incident splitting engine."""

    def setUp(self):
        self.splitter = get_incident_splitter()

    @tier(1)
    def test_single_sin_scenarios_remain_single_incident(self):
        """All 10 canonical scenarios must remain exactly 1 unified incident."""
        for sc_id, sc in TEN_SCENARIOS.items():
            text = sc["input_text"]
            incidents = split_confession_incidents(text)
            self.assertEqual(
                len(incidents), 1,
                f"Scenario {sc_id} ('{sc['title']}') was erroneously split into {len(incidents)} incidents!"
            )
            # Ensure description retains context and closing questions/remorse
            desc = incidents[0].description
            self.assertTrue(len(desc) >= len(text.strip()) - 5)
            self.assertIn(text[:20], desc)

    @tier(1)
    def test_compound_confession_tier3_splitting(self):
        """Tier 3 canonical test: compound confession of theft + alcohol/prayer."""
        compound_text = (
            "I går begik jeg to store fejl. Først stjal jeg 500 kr fra min vens taske på arbejdet. "
            "Senere på aftenen blev jeg så fortvivlet, at jeg drak alkohol og sprang Isha-bønnen over."
        )
        incidents = split_confession_incidents(compound_text)
        self.assertTrue(len(incidents) >= 2, f"Expected at least 2 incidents, got {len(incidents)}")

        # Check theft incident
        theft_matches = [i for i in incidents if "stjal" in i.description.lower() or "500" in i.description]
        self.assertTrue(len(theft_matches) >= 1, "Theft incident was not properly extracted")

        # Check prayer/alcohol incident
        prayer_matches = [i for i in incidents if "bøn" in i.description.lower() or "alkohol" in i.description.lower()]
        self.assertTrue(len(prayer_matches) >= 1, "Prayer/alcohol incident was not properly extracted")

    @tier(1)
    def test_numbered_and_bulleted_lists(self):
        """Lists formatted with numbers or bullets must split into discrete incidents."""
        # Numbered list
        numbered_text = (
            "1. Jeg stjal 1.000 kr fra min arbejdsgivers kasseapparat i fredags.\n"
            "2. Jeg bagtalte min leder over for alle mine kolleger bagefter."
        )
        inc_num = split_confession_incidents(numbered_text)
        self.assertEqual(len(inc_num), 2, f"Expected 2 incidents from numbered list, got {len(inc_num)}")
        self.assertIn("1.000", inc_num[0].description)
        self.assertIn("bagtalte", inc_num[1].description)

        # Bulleted list
        bullet_text = (
            "- Jeg slog min bror i et skænderi i går morges.\n"
            "- Jeg løj for min far og sagde, at jeg intet vidste om det."
        )
        inc_bullet = split_confession_incidents(bullet_text)
        self.assertEqual(len(inc_bullet), 2, f"Expected 2 incidents from bullet list, got {len(inc_bullet)}")
        self.assertIn("slog", inc_bullet[0].description)
        self.assertIn("løj", inc_bullet[1].description)

    @tier(1)
    def test_discourse_markers_derudover_desuden(self):
        """Additive conjunction discourse markers (Derudover, Desuden) with distinct sins split."""
        text = "Jeg stjal en cykel fra banegården i går. Derudover bagtalte jeg min nabo foran hele familien."
        incidents = split_confession_incidents(text)
        self.assertEqual(len(incidents), 2, f"Expected 2 incidents, got {len(incidents)}")
        self.assertIn("cykel", incidents[0].description)
        self.assertIn("bagtalte", incidents[1].description)

    @tier(1)
    def test_boundary_empty_and_whitespace(self):
        """Empty or whitespace text returns empty list safely."""
        self.assertEqual(split_confession_incidents(""), [])
        self.assertEqual(split_confession_incidents("   \t\n  "), [])
        self.assertEqual(split_confession_incidents(None), [])

    @tier(1)
    def test_danish_characters_preservation(self):
        """Danish characters (æ, ø, å, Æ, Ø, Å) are preserved without corruption."""
        danish_text = "Jeg stjal æbler og ødelagde et åbent hegn i Århus."
        incidents = split_confession_incidents(danish_text)
        self.assertEqual(len(incidents), 1)
        desc = incidents[0].description
        self.assertIn("æbler", desc)
        self.assertIn("ødelagde", desc)
        self.assertIn("åbent", desc)
        self.assertIn("Århus", desc)

    @tier(1)
    def test_to_incident_details_conversion(self):
        """Conversion to IncidentSchema/IncidentDetail produces valid schema instances."""
        text = "Jeg stjal 500 kr. Senere på aftenen drak jeg alkohol og sprang bønnen over."
        segments = split_confession_incidents(text)
        details = to_incident_details(segments, default_classification="both")
        self.assertEqual(len(details), len(segments))
        for d in details:
            self.assertEqual(d.sin_classification, "both")
            self.assertTrue(len(d.description) > 0)


if __name__ == "__main__":
    unittest.main()
