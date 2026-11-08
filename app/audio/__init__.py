"""
app/audio/__init__.py

Audio validation and speech-to-text transcription pipeline for voice confessions.
"""

from app.audio.validator import validate_audio_upload, ALLOWED_AUDIO_MIMES, MAX_AUDIO_BYTES
from app.audio.transcriber import AudioTranscriber, get_transcriber

__all__ = [
    "validate_audio_upload",
    "ALLOWED_AUDIO_MIMES",
    "MAX_AUDIO_BYTES",
    "AudioTranscriber",
    "get_transcriber",
]
