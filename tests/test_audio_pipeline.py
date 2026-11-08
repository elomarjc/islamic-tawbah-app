"""
Tier 1 & Tier 2 Test Suite: Voice Upload Validation & Speech-to-Text Pipeline.
Verifies audio MIME format validation, size constraints (25MB limit),
explicit consent guard, and deterministic offline mock transcription fallback.
"""

import io
import unittest

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


class TestAudioPipelineAndTranscription(unittest.TestCase):
    """
    Tier 1 & Tier 2: Voice intake, MIME validation, mock transcription fallback.
    """

    def setUp(self):
        if APP_AVAILABLE:
            self.client = TestClient(fastapi_app)
        else:
            self.client = None

    # ------------------------------------------------------------------------
    # Tier 1: Voice Upload & Validation (Happy Path & Fallback)
    # ------------------------------------------------------------------------
    @tier(1)
    @requires_app
    def test_voice_upload_webm_format_accepted(self):
        """Tier 1: Feature #19 - Accepts audio/webm with consent=true."""
        # Simulated WebM file
        dummy_webm = io.BytesIO(b"\x1a\x45\xdf\xa3" + b"\x00" * 1024)
        dummy_webm.name = "confession.webm"

        res = self.client.post(
            "/api/confessions/voice",
            files={"audio": ("confession.webm", dummy_webm, "audio/webm")},
            data={"consent": "true"}
        )
        self.assertIn(res.status_code, [200, 201])
        data = res.json()
        self.assertIn("transcript", data)
        self.assertIn("incident_summary", data)

    @tier(1)
    @requires_app
    def test_voice_upload_wav_format_accepted(self):
        """Tier 1: Feature #19 - Accepts audio/wav with consent=true."""
        dummy_wav = io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 512)
        dummy_wav.name = "confession.wav"

        res = self.client.post(
            "/api/confessions/voice",
            files={"audio": ("confession.wav", dummy_wav, "audio/wav")},
            data={"consent": "true"}
        )
        self.assertIn(res.status_code, [200, 201])

    @tier(1)
    @requires_app
    def test_transcription_pipeline_mock_fallback(self):
        """Tier 1: Feature #20 - Deterministic fallback transcriber operates without OpenAI key."""
        dummy_webm = io.BytesIO(b"\x1a\x45\xdf\xa3" + b"\x00" * 512)
        res = self.client.post(
            "/api/confessions/voice",
            files={"audio": ("confession.webm", dummy_webm, "audio/webm")},
            data={"consent": "true"}
        )
        self.assertIn(res.status_code, [200, 201])
        data = res.json()
        transcript = data.get("transcript", "")
        self.assertTrue(len(transcript) > 0, "Fallback transcriber must return non-empty Danish transcript")

    @tier(1)
    @requires_app
    def test_voice_recorder_interface_contract(self):
        """Tier 1: Feature #26 - MediaRecorder payload structure matches backend ingestion."""
        # Verify endpoint responds to multipart form containing audio and consent
        dummy_data = io.BytesIO(b"mock audio bytes")
        res = self.client.post(
            "/api/confessions/voice",
            files={"audio": ("recording.webm", dummy_data, "audio/webm")},
            data={"consent": "true"}
        )
        self.assertIn(res.status_code, [200, 201])

    # ------------------------------------------------------------------------
    # Tier 2: Boundary & Corner Cases (Audio MIME, Size, Consent)
    # ------------------------------------------------------------------------
    @tier(2)
    @requires_app
    def test_voice_upload_requires_explicit_consent(self):
        """Tier 2: Feature #27 - Rejects voice upload with 400 when consent=false or omitted."""
        dummy_audio = io.BytesIO(b"dummy audio")
        # consent=false
        res_false = self.client.post(
            "/api/confessions/voice",
            files={"audio": ("test.webm", dummy_audio, "audio/webm")},
            data={"consent": "false"}
        )
        self.assertEqual(res_false.status_code, 400)

        # consent omitted
        dummy_audio.seek(0)
        res_missing = self.client.post(
            "/api/confessions/voice",
            files={"audio": ("test.webm", dummy_audio, "audio/webm")}
        )
        self.assertEqual(res_missing.status_code, 400)

    @tier(2)
    @requires_app
    def test_voice_upload_rejects_invalid_mime_types(self):
        """Tier 2: Feature #19 - Rejects unsupported file types (text, pdf, images)."""
        # Text file
        text_data = io.BytesIO(b"This is text, not audio")
        res_txt = self.client.post(
            "/api/confessions/voice",
            files={"audio": ("notes.txt", text_data, "text/plain")},
            data={"consent": "true"}
        )
        self.assertIn(res_txt.status_code, [400, 415, 422])

        # PNG image
        img_data = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        res_img = self.client.post(
            "/api/confessions/voice",
            files={"audio": ("photo.png", img_data, "image/png")},
            data={"consent": "true"}
        )
        self.assertIn(res_img.status_code, [400, 415, 422])

    @tier(2)
    @requires_app
    def test_voice_upload_rejects_empty_audio_payload(self):
        """Tier 2: Feature #19 - Rejects 0-byte audio file."""
        empty_data = io.BytesIO(b"")
        res_empty = self.client.post(
            "/api/confessions/voice",
            files={"audio": ("empty.webm", empty_data, "audio/webm")},
            data={"consent": "true"}
        )
        self.assertIn(res_empty.status_code, [400, 422])

    @tier(2)
    @requires_app
    def test_voice_upload_rejects_oversized_payload_25mb(self):
        """Tier 2: Feature #19 - Rejects audio exceeding 25MB limit."""
        # Simulated oversized buffer header indicating >25MB
        oversized_data = io.BytesIO(b"0" * (26 * 1024 * 1024))  # 26 MB
        res_oversized = self.client.post(
            "/api/confessions/voice",
            files={"audio": ("large.webm", oversized_data, "audio/webm")},
            data={"consent": "true"}
        )
        self.assertIn(res_oversized.status_code, [400, 413, 422])


if __name__ == "__main__":
    unittest.main()
