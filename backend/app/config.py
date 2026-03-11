from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback for minimal test environments
    def load_dotenv(_path: Path | None = None) -> bool:
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE_PATH)


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def env_required(name: str) -> str:
    value = env(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
