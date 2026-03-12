from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - optional until dependencies are installed
    psycopg = None

from backend.app.config import env
from backend.app.services.embedding_service import embedding_configuration


PGVECTOR_DSN = env("PGVECTOR_DSN")


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
    config = embedding_configuration()
    configured_dimension = int(config["dimension"])
    configured_model_id = str(config["model_id"])
    configured_backend = str(config["backend"])

    with _connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vector_store_config (
                    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
                    embedding_backend TEXT NOT NULL,
                    embedding_model_id TEXT NOT NULL,
                    embedding_dim INTEGER NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            existing_dimension = _get_existing_vector_dimension(cursor)
            if existing_dimension is not None and existing_dimension != configured_dimension:
                raise RuntimeError(
                    "Configured embedding dimension does not match the existing pgvector schema. "
                    f"Configured={configured_dimension}, existing={existing_dimension}."
                )

            existing_config = cursor.execute(
                """
                SELECT embedding_backend, embedding_model_id, embedding_dim
                FROM vector_store_config
                WHERE id = 1;
                """
            ).fetchone()
            if existing_config:
                if (
                    str(existing_config[0]) != configured_backend
                    or str(existing_config[1]) != configured_model_id
                    or int(existing_config[2]) != configured_dimension
                ):
                    raise RuntimeError(
                        "Configured embedding backend/model does not match the initialized vector store. "
                        "Update the database or align EMBEDDING_MODEL_ID before startup."
                    )

            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    source_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding VECTOR({configured_dimension}) NOT NULL,
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
            cursor.execute(
                """
                INSERT INTO vector_store_config (id, embedding_backend, embedding_model_id, embedding_dim)
                VALUES (1, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET embedding_backend = EXCLUDED.embedding_backend,
                    embedding_model_id = EXCLUDED.embedding_model_id,
                    embedding_dim = EXCLUDED.embedding_dim,
                    updated_at = NOW();
                """,
                (configured_backend, configured_model_id, configured_dimension),
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
    config = embedding_configuration()
    return {
        "configured": bool(PGVECTOR_DSN),
        "embedding_dim": int(config["dimension"]),
        "embedding_backend": str(config["backend"]),
        "embedding_model_id": str(config["model_id"]),
    }


def _get_existing_vector_dimension(cursor) -> int | None:
    row = cursor.execute(
        """
        SELECT format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'document_chunks'
          AND a.attname = 'embedding'
          AND n.nspname = current_schema();
        """
    ).fetchone()
    if not row or not row[0]:
        return None
    formatted_type = str(row[0])
    if not formatted_type.startswith("vector(") or not formatted_type.endswith(")"):
        return None
    return int(formatted_type.removeprefix("vector(").removesuffix(")"))
