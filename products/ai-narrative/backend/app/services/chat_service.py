"""
chat_service.py — RAG-based chat over a user's ingested reference narratives.

Each chat turn:
  1. Embeds the user's question.
  2. Retrieves the most similar reference chunks owned by that user.
  3. Feeds the chunks as context to the LLM with a system prompt that
     understands NDA period notation (P-06, P-07, P-08 …).
  4. Returns the assistant reply plus source snippets for transparency.
"""
from __future__ import annotations

import re
from typing import Any

from backend.app.services.embedding_service import embed_query
from backend.app.services.llm_provider import LLMProvider, generate_text
from backend.app.services.vector_store import query_similar_references

_SYSTEM_PROMPT = """\
You are an expert analyst assistant for a Nuclear Decommissioning Authority (NDA) \
project portfolio. You have access to a library of project narratives uploaded by \
the user.

Key conventions you understand:
- Periods are denoted as P-01 through P-12 (e.g. P-06, P-07, P-08). Each period \
  is a reporting interval, typically four-weekly or monthly.
- Projects are identified by codes like "P06 | Project Name" where P06 is the period.
- RAG status: R = Red (major concern), A = Amber (minor concern), G = Green (on track).
- EAC = Estimate At Completion; P50 = 50th percentile cost; P80 = 80th percentile cost.
- OBC = Outline Business Case; FBC = Full Business Case.

Answer questions based ONLY on the provided reference narratives. If the answer is \
not in the references, say so clearly. Be concise, factual, and cite the source \
project by name when possible.
"""


def _extract_period_filter(text: str) -> str | None:
    """Return a canonical period string like 'P-06' if one is mentioned."""
    match = re.search(r"\bP[-\s]?0?(\d{1,2})\b", text, re.IGNORECASE)
    if match:
        return f"P-{match.group(1).zfill(2)}"
    return None


def _build_context(matches: list) -> str:
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
    provider: LLMProvider = "openai",
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

    last_user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        "",
    )

    # 1. Embed the user's question and retrieve relevant reference chunks
    try:
        query_vec = embed_query(last_user)
        matches = query_similar_references(
            user_id=user_id,
            query_embedding=query_vec,
            limit=top_k,
        )
    except Exception:
        matches = []

    # 2. Build the context block from retrieved chunks
    context_block = _build_context(matches) if matches else "(No reference narratives found in your library.)"

    # 3. Build the full message list for the LLM
    system_with_context = (
        _SYSTEM_PROMPT
        + f"\n\nREFERENCE NARRATIVES RETRIEVED FOR THIS QUESTION:\n\n{context_block}"
    )

    llm_messages: list[dict] = [{"role": "system", "content": system_with_context}]
    for m in messages:
        llm_messages.append({"role": m["role"], "content": m["content"]})

    # 4. Generate response
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