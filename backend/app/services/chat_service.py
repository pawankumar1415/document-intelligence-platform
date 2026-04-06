"""
chat_service.py — Conversational RAG pipeline with persistent session memory.

Each chat session is identified by a session_id UUID.  On the first call the server
creates a new session and returns the ID to the client; the client stores it and sends
it back on every subsequent message so history survives page refreshes.

Intent detection routes questions to the appropriate retrieval strategy:
  - document_search  → pgvector similarity search on indexed document chunks
  - general          → no retrieval; answer from LLM knowledge + context

The last MAX_HISTORY_MESSAGES messages (default 20) are injected into the LLM prompt
on each call.  Full history is retained in SQLite for audit purposes.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.services import persistence
from backend.app.services.llm_provider import LLMProvider, generate_json_object, generate_text

logger = logging.getLogger(__name__)

MAX_HISTORY_MESSAGES = 20

_INTENT_SYSTEM_PROMPT = """\
You are a router. Analyze the user's question about documents in the BSBI Document Intelligence Platform and determine the intent.
Output ONLY a JSON object with one key:
"intent": string. Choose from:
  - "document_search" (asking about content, details, or insights from uploaded documents)
  - "general" (greetings, unrelated questions, or questions about the platform itself)
"""

_ANSWER_SYSTEM_PROMPT = """\
You are the BSBI Document Intelligence Assistant, an expert AI that helps users explore and understand their uploaded documents.
You have been provided with relevant context retrieved from the user's documents.

Answer the user's question based on the provided Context Data.
If the context does not contain the answer, say "I don't have enough information in the uploaded documents to answer that."
Do not make up facts or figures.

Formatting rules:
- Use Markdown for clear, readable responses.
- Be professional, concise, and grounded in the source material.
- If no document context is available, answer from general knowledge but state that clearly.
"""


def _detect_intent(question: str, provider: LLMProvider, model: str | None) -> str:
    """Classify the user's question to determine the retrieval strategy."""
    try:
        result = generate_json_object(
            provider=provider,
            system_prompt=_INTENT_SYSTEM_PROMPT,
            user_prompt=question,
            temperature=0.0,
            model=model,
        )
        intent = result.get("intent", "document_search")
        return intent if intent in ("document_search", "general") else "document_search"
    except Exception:
        logger.warning("Intent detection failed; defaulting to document_search", exc_info=True)
        return "document_search"


def _vector_search(
    question: str,
    user_id: int,
    project_id: int | None,
    top_k: int = 5,
) -> str:
    """Retrieve semantically similar document chunks from pgvector."""
    try:
        from backend.app.services.embedding_service import embed_query
        from backend.app.services.vector_store import query_similar_chunks

        query_embedding = embed_query(question)

        if project_id is not None:
            matches = query_similar_chunks(
                user_id=user_id,
                project_id=project_id,
                query_embedding=query_embedding,
                limit=top_k,
            )
        else:
            # Search across all user projects by querying without project filter
            matches = _query_all_projects(user_id=user_id, query_embedding=query_embedding, limit=top_k)

        if not matches:
            return "No relevant content found in the uploaded documents."

        context = "RETRIEVED DOCUMENT CONTEXT:\n"
        for i, match in enumerate(matches, 1):
            context += f"--- Chunk {i} [Relevance: {match.score:.2f}] ---\n{match.content}\n\n"
        return context

    except Exception as exc:
        logger.warning("Vector search failed: %s", exc, exc_info=True)
        return "Document search is currently unavailable."


def _query_all_projects(user_id: int, query_embedding: list[float], limit: int) -> list[Any]:
    """Query chunks across all projects belonging to a user."""
    try:
        from backend.app.services.vector_store import _connect, _ensure_vector_literal, ChunkMatch

        with _connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT content, 1 - (embedding <=> %s::vector) AS score
                    FROM document_chunks
                    WHERE user_id = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s;
                    """,
                    (
                        _ensure_vector_literal(query_embedding),
                        user_id,
                        _ensure_vector_literal(query_embedding),
                        limit,
                    ),
                )
                rows = cursor.fetchall()
        return [ChunkMatch(content=row[0], score=float(row[1])) for row in rows]
    except Exception as exc:
        logger.warning("Cross-project vector search failed: %s", exc, exc_info=True)
        return []


def run_chat(
    question: str,
    user_id: int,
    session_id: str | None = None,
    project_id: int | None = None,
    provider: LLMProvider = "openai",
    model: str | None = None,
) -> dict[str, Any]:
    """
    Main entry point for POST /api/v1/chat.

    Flow:
      1. Resolve session (create new or validate supplied session_id).
      2. Load history from SQLite.
      3. Detect intent.
      4. Retrieve RAG context based on intent.
      5. Build LLM message list (system + history + augmented user message).
      6. Generate answer.
      7. Persist the user/assistant exchange (raw question, not augmented).
      8. Return answer + session_id + meta.

    Returns:
        {
            "answer": str,
            "session_id": str,
            "meta": {"intent": str, "context_length": int, "is_new_session": bool}
        }
    """
    # ── 1. Resolve session ────────────────────────────────────────────────────
    is_new_session = False

    if session_id and persistence.chat_session_exists(session_id):
        logger.info("Resuming chat session %s", session_id)
        effective_history = persistence.load_chat_history(session_id, max_messages=MAX_HISTORY_MESSAGES)
    else:
        if session_id:
            logger.warning("session_id %s not found — creating new session", session_id)
        session_id = persistence.create_chat_session(
            user_id=user_id,
            project_id=project_id,
            metadata={"provider": provider, "model": model or ""},
        )
        is_new_session = True
        logger.info("Created new chat session %s", session_id)
        effective_history = []

    # ── 2. Detect intent ──────────────────────────────────────────────────────
    intent = _detect_intent(question, provider, model)
    logger.info("Chat — intent: %s, session: %s, user: %s", intent, session_id, user_id)

    # ── 3. Retrieve context ───────────────────────────────────────────────────
    if intent == "document_search":
        context = _vector_search(question, user_id=user_id, project_id=project_id)
    else:
        context = "No document context needed for this question."

    # ── 4. Build LLM messages ─────────────────────────────────────────────────
    messages: list[dict] = [{"role": "system", "content": _ANSWER_SYSTEM_PROMPT}]
    messages.extend(effective_history)
    augmented_user_message = f"CONTEXT DATA:\n{context}\n\nUSER QUESTION:\n{question}"
    messages.append({"role": "user", "content": augmented_user_message})

    # ── 5. Generate answer ────────────────────────────────────────────────────
    try:
        answer = generate_text(
            provider=provider,
            messages=messages,
            temperature=0.4,
            model=model,
        )
    except Exception as exc:
        logger.error("LLM generation failed: %s", exc, exc_info=True)
        raise RuntimeError(f"Failed to generate answer: {exc}") from exc

    # ── 6. Persist exchange (raw question, not augmented) ─────────────────────
    try:
        persistence.save_chat_turn(
            session_id=session_id,
            user_message=question,
            assistant_message=answer,
            metadata={"intent": intent, "context_length": len(context)},
        )
    except Exception:
        logger.warning("Failed to persist chat turn for session %s", session_id, exc_info=True)

    return {
        "answer": answer,
        "session_id": session_id,
        "meta": {
            "intent": intent,
            "context_length": len(context),
            "is_new_session": is_new_session,
        },
    }