from __future__ import annotations

import logging

from backend.app.models.schemas import ClauseRecord
from backend.app.services import persistence
from backend.app.services.llm_provider import generate_json_object

logger = logging.getLogger(__name__)

_EXTRACT_SYSTEM_PROMPT = """\
You are a knowledge management specialist. You identify reusable text blocks (clauses) from professional documents.
A "clause" is a self-contained paragraph or section that could be reused verbatim or with minor edits in future documents.

Good clauses include:
- Governance statements
- Scope boundaries and exclusions
- Assumption paragraphs
- Pricing or commercial frameworks
- Risk mitigation approaches
- Standard methodology descriptions
- Quality or compliance criteria

Rules:
- Extract only clauses that are truly reusable, not document-specific narrative.
- Each clause must be at least 2 sentences.
- Assign a short descriptive title (max 10 words) and 1-3 relevant tags.
- Return ONLY valid JSON — no markdown, no commentary outside the JSON.
"""

_EXTRACT_USER_PROMPT = """\
Extract reusable clauses from the document below.

Return JSON matching this schema exactly:
{{
  "clauses": [
    {{
      "title": "Short descriptive title",
      "content": "The exact text of the reusable clause",
      "tags": ["tag1", "tag2"]
    }}
  ]
}}

Extract between 3 and 10 clauses. Prefer quality over quantity.

Document — "{doc_name}":
{text}
"""


def auto_extract_clauses(
    text: str,
    doc_name: str,
    user_id: int,
    project_id: int | None,
    provider: str,
    model: str | None,
) -> list[ClauseRecord]:
    prompt = _EXTRACT_USER_PROMPT.format(doc_name=doc_name, text=text[:5000])

    try:
        raw = generate_json_object(
            system_prompt=_EXTRACT_SYSTEM_PROMPT,
            user_prompt=prompt,
            provider=provider,
            model=model,
        )
    except Exception as exc:
        logger.warning("Auto-extract clauses failed: %s", exc)
        return []

    clauses_raw = raw.get("clauses", []) if isinstance(raw.get("clauses"), list) else []
    saved: list[ClauseRecord] = []

    for c in clauses_raw:
        if not isinstance(c, dict):
            continue
        content = (c.get("content") or "").strip()
        title = (c.get("title") or "Untitled Clause").strip()
        tags = c.get("tags", []) if isinstance(c.get("tags"), list) else []
        if len(content) < 20:
            continue
        record = persistence.save_clause(
            user_id=user_id,
            project_id=project_id,
            title=title,
            content=content,
            tags=tags,
            source_doc=doc_name,
        )
        saved.append(ClauseRecord(
            id=record["id"],
            title=record["title"],
            content=record["content"],
            tags=record["tags"],
            source_doc=record["source_doc"],
            project_id=record["project_id"],
            created_at=record["created_at"],
        ))

    return saved


def search_clauses_semantic(user_id: int, query: str, limit: int = 10) -> list[ClauseRecord]:
    """Keyword-ranked search across all clauses for the user."""
    return _keyword_search_clauses(user_id, query, limit)


def _keyword_search_clauses(user_id: int, query: str, limit: int) -> list[ClauseRecord]:
    """Simple keyword fallback: filter locally by query terms."""
    all_clauses = persistence.list_clauses(user_id)
    query_lower = query.lower()
    keywords = query_lower.split()
    scored: list[tuple[int, dict]] = []
    for c in all_clauses:
        text = (c["title"] + " " + c["content"] + " " + " ".join(c["tags"])).lower()
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        ClauseRecord(
            id=c["id"],
            title=c["title"],
            content=c["content"],
            tags=c["tags"],
            source_doc=c["source_doc"],
            project_id=c["project_id"],
            created_at=c["created_at"],
        )
        for _, c in scored[:limit]
    ]


def save_clause_and_index(
    user_id: int,
    project_id: int | None,
    title: str,
    content: str,
    tags: list[str],
    source_doc: str,
) -> ClauseRecord:
    """Save a clause to SQLite and index it in pgvector."""
    record = persistence.save_clause(
        user_id=user_id,
        project_id=project_id,
        title=title,
        content=content,
        tags=tags,
        source_doc=source_doc,
    )
    clause_id = record["id"]

    return ClauseRecord(
        id=clause_id,
        title=record["title"],
        content=record["content"],
        tags=record["tags"],
        source_doc=record["source_doc"],
        project_id=record["project_id"],
        created_at=record["created_at"],
    )