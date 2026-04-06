from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def build_output_path(prefix: str, suffix: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return ensure_output_dir() / f"{prefix}-{timestamp}.{suffix}"
