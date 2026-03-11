from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - optional until dependencies are installed
    psycopg = None

from backend.app.config import env


PGVECTOR_DSN = env("PGVECTOR_DSN")
EMBEDDING_DIM = int(env("EMBEDDING_DIM", "1536") or "1536")


@dataclass
class ChunkMatch:
    content: str
    score: float


def _ensure_vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def _connect() -> psycopg.Connection:
    if psycopg is None:
        raise RuntimeError("psycopg is not installed. Install requirements.txt dependencies.")
    if not PGVECTOR_DSN:
        raise RuntimeError("PGVECTOR_DSN is not configured.")
    return psycopg.connect(PGVECTOR_DSN)


def init_vector_store() -> None:
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    source_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR({EMBEDDING_DIM}) NOT NULL,
                    provider TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_document_chunks_source
                ON document_chunks (source_id);
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_document_chunks_project
                ON document_chunks (project_id);
                """
            )
        connection.commit()


def upsert_chunks(
    *,
    user_id: int,
    project_id: int,
    source_id: str,
    provider: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("Chunks and embeddings length mismatch.")

    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM document_chunks WHERE source_id = %s;", (source_id,))
            for index, (chunk, vector) in enumerate(zip(chunks, embeddings)):
                cursor.execute(
                    """
                    INSERT INTO document_chunks (
                        user_id, project_id, source_id, chunk_index, content, embedding, provider
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::vector, %s);
                    """,
                    (
                        user_id,
                        project_id,
                        source_id,
                        index,
                        chunk,
                        _ensure_vector_literal(vector),
                        provider,
                    ),
                )
        connection.commit()


def query_similar_chunks(
    *,
    user_id: int,
    project_id: int,
    query_embedding: list[float],
    limit: int = 5,
) -> list[ChunkMatch]:
    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT content, 1 - (embedding <=> %s::vector) AS score
                FROM document_chunks
                WHERE user_id = %s AND project_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (
                    _ensure_vector_literal(query_embedding),
                    user_id,
                    project_id,
                    _ensure_vector_literal(query_embedding),
                    limit,
                ),
            )
            rows = cursor.fetchall()

    return [ChunkMatch(content=row[0], score=float(row[1])) for row in rows]


def vector_store_status() -> dict[str, Any]:
    return {
        "configured": bool(PGVECTOR_DSN),
        "embedding_dim": EMBEDDING_DIM,
    }
