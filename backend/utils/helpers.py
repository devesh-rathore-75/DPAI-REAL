"""
DPAI — Utility Helpers
Common utility functions used across the application.
"""

import os
import uuid
import hashlib
from datetime import datetime
from pathlib import Path


# ── Directories ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RESULTS_DIR = DATA_DIR / "results"

for d in [DATA_DIR, UPLOAD_DIR, RESULTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def generate_id() -> str:
    """Generate a short unique ID for tracking documents."""
    return uuid.uuid4().hex[:12]


def file_hash(content: bytes) -> str:
    """SHA-256 hash of file content for duplicate detection."""
    return hashlib.sha256(content).hexdigest()


def timestamp_now() -> str:
    """ISO-formatted timestamp."""
    return datetime.utcnow().isoformat() + "Z"


def allowed_extension(filename: str) -> bool:
    """Check if the file extension is supported."""
    allowed = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed


def get_file_extension(filename: str) -> str:
    """Return the lowercase file extension."""
    return os.path.splitext(filename)[1].lower()
