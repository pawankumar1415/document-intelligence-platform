from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(_path: Path | None = None) -> bool:
        return False

# Product root is products/ai-narrative/ (2 levels above this file)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE_PATH)


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_json(name: str, default: object | None = None) -> object | None:
    value = env(name)
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Environment variable {name} does not contain valid JSON.") from exc


def env_required(name: str) -> str:
    value = env(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value