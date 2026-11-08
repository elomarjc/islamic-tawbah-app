"""
tests/test_frontend_and_e2e.py

Milestone 3, 4 & 5 End-to-End Verification Suite:
- Frontend SPA static asset delivery (HTML, CSS tokens, JS modules)
- Danish copy & 6-page navigation verification
- Design system token verification (#16382B Forest Green, #FBF9F5 Warm Off-White, #C29B38 Gold)
- Voice confession end-to-end persistence & transcript_hint support
- Compound multi-sin confession ("mor + far 25 kroner") end-to-end verification
- Action checklist toggle persistence reflected in GET /api/confessions/{id}
- Knowledge base API search and filtering
"""

import io
import unittest
from fastapi.testclient import TestClient

from tests.test_base import tier, requires_app
from app.main import app as fastapi_app


class TestFrontendAndEndToEndFlows(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(fastapi_app)

    @tier(1)
    @requires_app
    def test_frontend_spa_and_design_tokens_served(self):
        """Tier 1: Features #24, #25 - Frontend index.html, CSS tokens, and JS modules serve cleanly."""
        res_html = self.client.get("/")
        self.assertEqual(res_html.status_code, 200)
        html = res_html.text

        # Required Danish headline and subtitle from Master Prompt Section 10
        self.assertIn("Tag ansvar. Søg tilgivelse. Gør det godt igen.", html)
        self.assertIn(
          "Fortæl, hvad du har gjort. Få hjælp til at forstå dine islamiske forpligtelser og de handlinger, du bør tage.",
          html,
        )

        # All 6 core navigation pages present in Danish
        for nav_label in [
            "Hjem",
            "Ny bekendelse",
            "Mine handlinger",
            "Historik",
            "Islamisk viden",
            "Indstillinger",
        ]:
            self.assertIn(nav_label, html)

        # Verify CSS design tokens (#16382B, #FBF9F5, #C29B38)
        res_vars = self.client.get("/css/variables.css")
        self.assertEqual(res_vars.status_code, 200)
        css_vars = res_vars.text
        self.assertIn("#16382B", css_vars)
        self.assertIn("#FBF9F5", css_vars)
        self.assertIn("#C29B38", css_vars)

        # Verify layout and component CSS + JS modules
        for asset in [
            "/css/layout.css",
            "/css/components.css",
            "/js/app.js",
            "/js/api.js",
            "/js/audio_recorder.js",
            "/js/ui.js",
        ]:
            r = self.client.get(asset)
            self.assertEqual(r.status_code, 200, f"Failed to serve frontend asset {asset}")

    @tier(3)
    @requires_app
    def test_compound_mother_and_father_confession_e2e(self):
        """Tier 3: Feature #8 & Master Prompt Section 4 example (Mother disrespect + Father 25 kr theft)."""
        confession_text = (
            "Jeg talte respektløst til min mor i dag og gjorde grin med hendes vægt. "
            "Senere stjal jeg 25 kroner fra min far."
        )
        res = self.client.post(
            "/api/confessions/text",
            json={"text": confession_text, "consent": True},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["sin_classification"], "both")
        self.assertGreaterEqual(len(data["incidents"]), 2, "Must split mother insult and father theft into >=2 incidents")
        self.assertTrue(len(data["required_actions"]) >= 2)
        self.assertTrue(len(data["quran_references"]) >= 1)
        self.assertTrue(len(data["hadith_references"]) >= 1)

    @tier(3)
    @requires_app
    def test_voice_confession_with_transcript_hint_and_checklist_sync(self):
        """Tier 3: Features #19, #20, #22, #32 - Voice confession persists actions and syncs toggle state on reload."""
        wav_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 512
        hint = "Jeg bagtalte min kollega i frokostpausen og fortryder det dybt."

        res = self.client.post(
            "/api/confessions/voice",
            files={"audio": ("confession.wav", io.BytesIO(wav_bytes), "audio/wav")},
            data={"consent": "true", "transcript_hint": hint},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["transcript"], hint)
        self.assertFalse(data["demonstration_mode"])

        conf_id = data["confession_id"]
        first_action_id = data["required_actions"][0]["id"]

        # Toggle first required action to completed=True
        res_toggle = self.client.patch(
            f"/api/actions/{first_action_id}",
            json={"completed": True},
        )
        self.assertEqual(res_toggle.status_code, 200)

        # Fetch confession by ID and verify the action item's completed state is synced
        res_get = self.client.get(f"/api/confessions/{conf_id}")
        self.assertEqual(res_get.status_code, 200)
        reloaded = res_get.json()
        matching = [a for a in reloaded["required_actions"] if a["id"] == first_action_id]
        self.assertTrue(matching and matching[0]["completed"], "Reloaded confession must reflect toggled action status")

    @tier(1)
    @requires_app
    def test_knowledge_base_endpoint_and_filtering(self):
        """Tier 1: Feature #36 - Knowledge base API returns verified Quran, Hadith, Duas, and Fiqh rules."""
        res = self.client.get("/api/knowledge")
        self.assertEqual(res.status_code, 200)
        kb = res.json()
        self.assertGreater(len(kb.get("quran", [])), 5)
        self.assertGreater(len(kb.get("hadith", [])), 5)
        self.assertGreater(len(kb.get("duas", [])), 3)
        self.assertGreater(len(kb.get("fiqh_rules", [])), 3)

        # Filtered query
        res_filtered = self.client.get("/api/knowledge?q=Zumar")
        self.assertEqual(res_filtered.status_code, 200)
        kb_f = res_filtered.json()
        self.assertGreaterEqual(len(kb_f.get("quran", [])), 1)


if __name__ == "__main__":
    unittest.main()
