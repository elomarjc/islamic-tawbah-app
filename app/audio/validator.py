"""
app/audio/validator.py

Audio Upload Validation (Feature #19).
Enforces explicit consent, non-empty payload, <= 25 MB size boundary,
and supported MIME types / file extensions for browser MediaRecorder uploads.
"""

from __future__ import annotations

from typing import Optional, Set
from fastapi import HTTPException, UploadFile

MAX_AUDIO_BYTES: int = 25 * 1024 * 1024  # 25 MB

ALLOWED_AUDIO_MIMES: Set[str] = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/aac",
}

ALLOWED_AUDIO_EXTENSIONS: Set[str] = {
    ".webm",
    ".wav",
    ".mp4",
    ".m4a",
    ".mp3",
    ".ogg",
    ".aac",
}


async def validate_audio_upload(
    audio: Optional[UploadFile],
    consent: Optional[str],
) -> bytes:
    """
    Validates an incoming voice confession upload and returns the raw audio bytes.
    Raises HTTPException with appropriate status codes (400, 413, 415) on failure.
    """
    # 1. Explicit affirmative consent check
    if not consent or str(consent).strip().lower() not in ("true", "1"):
        raise HTTPException(
            status_code=400,
            detail="Eksplicit samtykke er påkrævet for at behandle en lydoptagelse.",
        )

    # 2. Audio file presence
    if audio is None:
        raise HTTPException(
            status_code=400,
            detail="Ingen lydfil modtaget.",
        )

    content = await audio.read()
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="Lydfilen er tom (0 bytes).",
        )

    # 3. Maximum size limit (25 MB)
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Lydfilen overstiger maksimumgrænsen på 25 MB.",
        )

    # 4. MIME type & extension validation
    raw_content_type = (audio.content_type or "").lower().split(";")[0].strip()
    filename = (audio.filename or "").lower().strip()

    mime_ok = raw_content_type in ALLOWED_AUDIO_MIMES
    ext_ok = any(filename.endswith(ext) for ext in ALLOWED_AUDIO_EXTENSIONS)

    # Reject non-audio MIME types even if filename is missing or ambiguous
    if not mime_ok and not (not raw_content_type and ext_ok):
        raise HTTPException(
            status_code=415,
            detail=f"Ikke understøttet lydformat: {raw_content_type or 'ukendt'}. Brug WebM, WAV, MP4 eller OGG.",
        )

    return content
