"""
app/audio/transcriber.py

Speech-to-Text Pipeline (Feature #20).
Supports:
1. Client-side / Browser SpeechRecognition Danish transcript hint (when provided by the user's browser).
2. OpenAI Whisper API (`whisper-1`, language=`da`) when `OPENAI_API_KEY` is configured.
3. Deterministic offline Danish fallback transcriber for development & testing mode.
"""

from __future__ import annotations

import io
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger("tawbah.audio.transcriber")

DEFAULT_DEMO_TRANSCRIPT = (
    "Jeg kom op at skændes med min kollega i frokostpausen og bagtalte ham "
    "foran de andre. Jeg skammer mig og søger Allahs tilgivelse."
)

SCENARIO_DEMO_TRANSCRIPTS: Dict[str, str] = {
    "mother": "Jeg talte respektløst til min mor i dag og hævede stemmen over for hende.",
    "father": "Jeg tog 500 kroner fra min fars pung uden hans tilladelse.",
    "combined": "Jeg talte respektløst til min mor i dag og gjorde grin med hendes vægt. Senere stjal jeg 25 kroner fra min far.",
    "fajr": "Jeg slukkede vækkeuret og sov bevidst videre over Fajr-bønnen i morges.",
    "spouse": "Jeg løj over for min ægtefælle om, hvad jeg havde brugt vores opsparing på.",
    "neighbor": "Jeg kom til at ridse min nabos bil og kørte videre uden at lægge en seddel.",
    "private": "Jeg begik en synd i det skjulte alene om natten, som ingen andre kender til.",
    "slander": "Jeg spredte et falsk rygte om en bekendt i vores gruppechat, selvom det ikke passede.",
    "trust": "Jeg brugte 5.000 kroner fra foreningens kasse til mine egne regninger.",
}


class AudioTranscriber:
    """
    Hybrid Speech-to-Text service with OpenAI Whisper integration and
    deterministic Danish fallback for offline/development environments.
    """

    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        self.offline_mode = os.environ.get("OFFLINE_MODE", "true").lower() in ("true", "1", "yes")

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "confession.webm",
        content_type: str = "audio/webm",
        transcript_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transcribes Danish audio into text.
        Returns dict with:
          - transcript: str
          - demonstration_mode: bool
          - engine: str ('browser_speech' | 'openai_whisper' | 'offline_demo')
        """
        # 1. If the user's browser Web Speech API captured a Danish transcript, use it
        if transcript_hint and isinstance(transcript_hint, str) and transcript_hint.strip():
            cleaned_hint = transcript_hint.strip()
            return {
                "transcript": cleaned_hint,
                "demonstration_mode": False,
                "engine": "browser_speech",
            }

        # 2. If OpenAI API key is configured and online mode is active, try OpenAI Whisper
        if self.api_key and not self.offline_mode:
            try:
                import urllib.request
                import json as _json
                import uuid

                boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
                body = io.BytesIO()

                # file field
                body.write(f"--{boundary}\r\n".encode("utf-8"))
                body.write(
                    f'Content-Disposition: form-data; name="file"; filename="{filename or "audio.webm"}"\r\n'.encode("utf-8")
                )
                body.write(f"Content-Type: {content_type or 'audio/webm'}\r\n\r\n".encode("utf-8"))
                body.write(audio_bytes)
                body.write(b"\r\n")

                # model field
                body.write(f"--{boundary}\r\n".encode("utf-8"))
                body.write(b'Content-Disposition: form-data; name="model"\r\n\r\nwhisper-1\r\n')

                # language field
                body.write(f"--{boundary}\r\n".encode("utf-8"))
                body.write(b'Content-Disposition: form-data; name="language"\r\n\r\nda\r\n')
                body.write(f"--{boundary}--\r\n".encode("utf-8"))

                req = urllib.request.Request(
                    "https://api.openai.com/v1/audio/transcriptions",
                    data=body.getvalue(),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": f"multipart/form-data; boundary={boundary}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    resp_data = _json.loads(resp.read().decode("utf-8"))
                    whisper_text = resp_data.get("text", "").strip()
                    if whisper_text:
                        return {
                            "transcript": whisper_text,
                            "demonstration_mode": False,
                            "engine": "openai_whisper",
                        }
            except Exception as ex:
                logger.warning("OpenAI Whisper transcription failed, using fallback: %s", ex)

        # 3. Deterministic offline fallback transcriber
        fname_lower = (filename or "").lower()
        for key, text in SCENARIO_DEMO_TRANSCRIPTS.items():
            if key in fname_lower:
                return {
                    "transcript": text,
                    "demonstration_mode": True,
                    "engine": "offline_demo",
                }

        return {
            "transcript": DEFAULT_DEMO_TRANSCRIPT,
            "demonstration_mode": True,
            "engine": "offline_demo",
        }


_transcriber_instance: Optional[AudioTranscriber] = None


def get_transcriber() -> AudioTranscriber:
    """Singleton accessor for AudioTranscriber."""
    global _transcriber_instance
    if _transcriber_instance is None:
        _transcriber_instance = AudioTranscriber()
    return _transcriber_instance
