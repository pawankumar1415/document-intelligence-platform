"""
domain_detector.py — Automatic domain detection from uploaded narrative samples.

Analyses a sample of narratives using an LLM to extract:
  - Domain name and industry
  - Reporting period format and label (e.g. P-XX, Quarter X, Phase X)
  - Status codes and their meanings
  - Key terminology and abbreviations
  - Domain-aware suggested chat questions

The resulting DomainProfile is stored per-user in SQLite and drives:
  - Dynamic chat system prompts tailored to the detected domain
  - Suggested questions in the chat UI
  - Period filter labels
"""
from __future__ import annotations

import logging
from typing import Any

from backend.app.config import default_llm_provider
from backend.app.services.llm_provider import LLMProvider, generate_json_object

logger = logging.getLogger(__name__)

_DETECT_SYSTEM = """\
You are a domain analysis expert. You will be given a sample of project narrative \
texts from an organisation's reporting system. Your job is to identify the domain, \
reporting conventions, and key terminology so an AI assistant can answer questions \
about this data intelligently.

Return ONLY valid JSON with exactly these keys:
{
  "domain_name": "<full organisation/domain name, e.g. 'Nuclear Decommissioning Authority'>",
  "period_label": "<what reporting cycles are called, e.g. 'Period', 'Quarter', 'Phase', 'Sprint'>",
  "period_format": "<how periods are written, e.g. 'P-XX (e.g. P-06, P-07)', 'Q1-Q4', 'Phase 1-5', or null if no cycles>",
  "status_codes": {
    "<code>": "<meaning>",
    ...
  },
  "key_terms": {
    "<abbreviation>": "<full meaning>",
    ...
  },
  "suggested_questions": [
    "<5 specific, useful questions a user might ask about this data>",
    ...
  ],
  "confidence": <0.0-1.0 how confident you are in this detection>
}

Rules:
- If you cannot determine a field, use null for strings and {} or [] for objects/arrays.
- suggested_questions must be specific to THIS domain's conventions and terminology.
- key_terms should only include terms actually present in the sample narratives.
- confidence >= 0.8 means you are highly confident in the domain identification.
"""

_DETECT_USER_TEMPLATE = """\
Analyse these {count} sample narratives and identify the domain and reporting conventions:

{samples}
"""


def detect_domain(
    sample_records: list[dict],
    provider: LLMProvider | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Analyse sample narrative records and return a domain profile dict.

    sample_records: list of {unique_id, narrative_text} dicts (up to 10 used).

    Returns a dict matching the DomainProfile schema, or a minimal fallback
    dict if detection fails.
    """
    provider = provider or default_llm_provider()  # type: ignore[assignment]
    samples = sample_records[:10]
    if not samples:
        return _fallback_profile()

    sample_text = "\n\n".join(
        f"--- Record {i + 1} (ID: {r.get('unique_id', 'unknown')}) ---\n{r.get('narrative_text', '')[:600]}"
        for i, r in enumerate(samples)
        if r.get("narrative_text", "").strip()
    )

    if not sample_text.strip():
        return _fallback_profile()

    try:
        raw = generate_json_object(
            system_prompt=_DETECT_SYSTEM,
            user_prompt=_DETECT_USER_TEMPLATE.format(count=len(samples), samples=sample_text),
            provider=provider,
            model=model,
            temperature=0.1,
        )
        return _normalise(raw)
    except Exception as exc:
        logger.warning("Domain detection failed: %s", exc)
        return _fallback_profile()


def _normalise(raw: dict) -> dict[str, Any]:
    """Ensure the profile dict has all required keys with correct types."""
    return {
        "domain_name": raw.get("domain_name") or None,
        "period_label": raw.get("period_label") or "Period",
        "period_format": raw.get("period_format") or None,
        "status_codes": raw.get("status_codes") if isinstance(raw.get("status_codes"), dict) else {},
        "key_terms": raw.get("key_terms") if isinstance(raw.get("key_terms"), dict) else {},
        "suggested_questions": [
            str(q) for q in (raw.get("suggested_questions") or []) if q
        ][:8],
        "confidence": float(raw.get("confidence") or 0.0),
    }


def _fallback_profile() -> dict[str, Any]:
    return {
        "domain_name": None,
        "period_label": "Period",
        "period_format": None,
        "status_codes": {},
        "key_terms": {},
        "suggested_questions": [],
        "confidence": 0.0,
    }