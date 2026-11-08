"""
app/config.py

Global application configuration and environment settings.
"""

import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
KNOWLEDGE_DIR = PROJECT_ROOT / "app" / "knowledge"
AUDIO_DIR = DATA_DIR / "audio"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Database Configuration
DEFAULT_DB_PATH = str(DATA_DIR / "tawbah.db")
DB_PATH = os.getenv("TAWBAH_DB_PATH", DEFAULT_DB_PATH)

# Environment & Application Mode
APP_ENV = os.getenv("APP_ENV", "development")  # 'development', 'production', 'test'
DEBUG = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")

# Offline / Fallback Engine Flag
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "true").lower() in ("true", "1", "yes")

# Audio Limits
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/wav", "audio/mp4", "audio/mpeg", "audio/ogg"}

# Security & Session Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "tawbah-insecure-secret-key-change-in-production")
SESSION_COOKIE_NAME = "session_token"
REGISTERED_SESSION_DAYS = 30
GUEST_SESSION_DAYS = 7

# Password Hashing Constants
PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 100_000
PBKDF2_SALT_BYTES = 16
