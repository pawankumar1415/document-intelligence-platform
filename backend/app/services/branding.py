from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOGO_PATH = PROJECT_ROOT / "frontend" / "public" / "bsbi-logo.jpeg"
PPT_TEMPLATE_PATH = PROJECT_ROOT / "backend" / "data" / "NDA AI Narrative - Show&Tell.pptx"


def logo_exists() -> bool:
    return LOGO_PATH.exists() and LOGO_PATH.is_file()


def ppt_template_exists() -> bool:
    return PPT_TEMPLATE_PATH.exists() and PPT_TEMPLATE_PATH.is_file()
