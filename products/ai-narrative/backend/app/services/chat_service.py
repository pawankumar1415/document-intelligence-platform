"""
chat_service.py — RAG-based chat over a user's ingested reference narratives.

Each chat turn:
  1. Loads the user's detected domain profile (auto-detected on reference ingest).
  2. Embeds the user's question.
  3. Retrieves the most similar narrative chunks owned by that user.
  4. Builds a domain-aware system prompt from the profile.
  5. Returns the assistant reply plus source snippets for transparency.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from backend.app.config import default_llm_provider
from backend.app.services.embedding_service import embed_query
from backend.app.services.llm_provider import LLMProvider, generate_text
from backend.app.services.vector_store import query_all_narratives

logger = logging.getLogger(__name__)

_BASE_SYSTEM = """\
You are an expert analyst assistant for a project portfolio reporting system. \
You have access to a library of project narratives uploaded by the user.

When reference narratives are provided, answer from them and cite the source project \
by name or ID. If no references are available or the answer is not in the references, \
still try to answer using your general knowledge of project reporting conventions — \
but clearly state that you are not drawing from uploaded documents. \
Be concise and factual.\
"""

_DOMAIN_CONTEXT_TEMPLATE = """\


DOMAIN CONTEXT (detected from uploaded data):
Domain: {domain_name}
{period_section}\
{status_section}\
{terms_section}\
"""


def _build_system_prompt(domain_profile: dict | None) -> str:
    """Compose the system prompt, injecting domain context if a profile exists."""
    if not domain_profile or not domain_profile.get("domain_name"):
        return _BASE_SYSTEM

    period_section = ""
    if domain_profile.get("period_format"):
        label = domain_profile.get("period_label", "Period")
        fmt = domain_profile["period_format"]
        period_section = f"Reporting {label}s: {fmt}\n"

    status_section = ""
    status_codes = domain_profile.get("status_codes") or {}
    if status_codes:
        lines = ", ".join(f"{k} = {v}" for k, v in status_codes.items())
        status_section = f"Status codes: {lines}\n"

    terms_section = ""
    key_terms = domain_profile.get("key_terms") or {}
    if key_terms:
        lines = ", ".join(f"{k} = {v}" for k, v in key_terms.items())
        terms_section = f"Key terms: {lines}\n"

    context = _DOMAIN_CONTEXT_TEMPLATE.format(
        domain_name=domain_profile["domain_name"],
        period_section=period_section,
        status_section=status_section,
        terms_section=terms_section,
    )
    return _BASE_SYSTEM + context


def _extract_period_filter(text: str) -> str | None:
    """Return a canonical period string like 'P-06' if one is mentioned."""
    match = re.search(r"\bP[-\s]?0?(\d{1,2})\b", text, re.IGNORECASE)
    if match:
        return f"P-{match.group(1).zfill(2)}"
    return None


def _build_context(matches: list) -> str:
    if not matches:
        return ""
    parts: list[str] = []
    for i, m in enumerate(matches, 1):
        parts.append(
            f"[{i}] Project: {m.unique_id}\n"
            f"{m.narrative_text[:800]}"
        )
    return "\n\n---\n\n".join(parts)


def run_chat(
    *,
    user_id: int,
    messages: list[dict[str, str]],
    provider: LLMProvider | None = None,
    model: str | None = None,
    top_k: int = 6,
) -> dict[str, Any]:
    """
    Process one chat turn.

    ``messages`` is the full conversation history in OpenAI format:
    [{"role": "user"|"assistant", "content": "..."}]

    Returns:
      {
        "reply": str,
        "sources": [{"unique_id": str, "excerpt": str, "score": float}]
      }
    """
    if not messages:
        raise ValueError("messages list is empty")
    provider = provider or default_llm_provider()  # type: ignore[assignment]

    last_user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        "",
    )

    # 1. Load domain profile to build context-aware system prompt
    from backend.app.services import persistence
    domain_profile = persistence.get_domain_profile(user_id)
    system_prompt = _build_system_prompt(domain_profile)

    # 2. Embed and retrieve relevant narratives
    retrieval_error: str | None = None
    matches = []
    try:
        query_vec = embed_query(last_user)
        matches = query_all_narratives(
            user_id=user_id,
            query_embedding=query_vec,
            limit=top_k,
        )
        logger.info("chat retrieval: user=%s question=%r matches=%d", user_id, last_user[:80], len(matches))
    except Exception as exc:
        retrieval_error = str(exc)
        logger.error("chat retrieval failed for user %s: %s", user_id, exc)

    if retrieval_error:
        if "different vector dimensions" in retrieval_error or "expected" in retrieval_error and "dimensions" in retrieval_error:
            raise RuntimeError(
                "Vector dimension mismatch: the embedding model has changed since the reference library was "
                "indexed. Set VECTOR_STORE_RESET_ON_MISMATCH=true and restart the backend, then re-ingest "
                "your reference files to rebuild the index."
            )
        raise RuntimeError(f"Failed to search reference library: {retrieval_error}")

    # 3. Build context block
    context_block = _build_context(matches) if matches else "(No reference narratives have been uploaded to your library yet.)"

    system_with_context = (
        system_prompt
        + f"\n\nREFERENCE NARRATIVES RETRIEVED FOR THIS QUESTION:\n\n{context_block}"
    )

    # 4. Build message list and generate
    llm_messages: list[dict] = [{"role": "system", "content": system_with_context}]
    for m in messages:
        llm_messages.append({"role": m["role"], "content": m["content"]})

    reply = generate_text(
        provider=provider,
        messages=llm_messages,
        temperature=0.3,
        model=model,
    )

    sources = [
        {
            "unique_id": m.unique_id,
            "excerpt": m.narrative_text[:300],
            "score": round(m.score, 3),
        }
        for m in matches
    ]

    return {"reply": reply, "sources": sources}