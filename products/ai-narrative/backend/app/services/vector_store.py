"""
vector_store.py — pgvector integration for reference narrative indexing.

Table: reference_narratives
  Stores embedded reference narratives uploaded by users.
  Used for semantic retrieval during scoring (find similar references).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

try:
    import psycopg
except ModuleNotFoundError:
    psycopg = None

from backend.app.config import env, env_bool
from backend.app.services.embedding_service import embedding_configuration

logger = logging.getLogger("ai_narrative.vector_store")

PGVECTOR_DSN = env("PGVECTOR_DSN")


@dataclass
class ReferenceMatch:
    unique_id: str
    narrative_text: str
    content: str
    score: float


def _ensure_vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def _connect() -> "psycopg.Connection":
    if psycopg is None:
        raise RuntimeError("psycopg is not installed. Run: pip install psycopg[binary]")
    if not PGVECTOR_DSN:
        raise RuntimeError("PGVECTOR_DSN is not configured in .env")
    return psycopg.connect(PGVECTOR_DSN)


def _ensure_database_exists() -> None:
    """Create the target database if it doesn't exist, connecting via the postgres maintenance db."""
    if not PGVECTOR_DSN:
        return
    try:
        psycopg.connect(PGVECTOR_DSN).close()
        return  # already exists
    except psycopg.OperationalError as exc:
        if "does not exist" not in str(exc):
            raise

    # Parse DSN to extract the database name and build a maintenance DSN
    import re
    match = re.search(r"/([^/?]+)(\?|$)", PGVECTOR_DSN)
    if not match:
        raise RuntimeError(f"Cannot parse database name from PGVECTOR_DSN: {PGVECTOR_DSN}")
    db_name = match.group(1)
    maintenance_dsn = PGVECTOR_DSN[: match.start()] + "/postgres" + PGVECTOR_DSN[match.end() - len(match.group(2)):]

    with psycopg.connect(maintenance_dsn, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{db_name}";')
    logger.info("Created database '%s'.", db_name)


def init_vector_store() -> None:
    _ensure_database_exists()
    config = embedding_configuration()
    configured_dimension = int(config["dimension"])
    configured_model_id = str(config["model_id"])
    configured_backend = str(config["backend"])
    reset_on_mismatch = env_bool("VECTOR_STORE_RESET_ON_MISMATCH", False)

    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vector_store_config (
                    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
                    embedding_backend  TEXT    NOT NULL,
                    embedding_model_id TEXT    NOT NULL,
                    embedding_dim      INTEGER NOT NULL,
                    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            existing_dim = _get_existing_dimension(cur, "reference_narratives")
            scored_dim = _get_existing_dimension(cur, "scored_narratives")
            mismatch_dim = existing_dim or scored_dim
            if mismatch_dim is not None and mismatch_dim != configured_dimension:
                if reset_on_mismatch:
                    _reset_schema(cur)
                    existing_dim = None
                else:
                    raise RuntimeError(
                        f"Embedding dimension mismatch: configured={configured_dimension}, "
                        f"existing={mismatch_dim}. Set VECTOR_STORE_RESET_ON_MISMATCH=true to reset "
                        f"(warning: all stored vectors will be deleted and reference files must be re-ingested)."
                    )

            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS reference_narratives (
                    id             BIGSERIAL PRIMARY KEY,
                    file_id        INTEGER   NOT NULL,
                    user_id        INTEGER   NOT NULL,
                    unique_id      TEXT      NOT NULL,
                    narrative_text TEXT      NOT NULL,
                    content        TEXT      NOT NULL,
                    embedding      VECTOR({configured_dimension}) NOT NULL,
                    indexed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_ref_narratives_file
                ON reference_narratives (file_id);
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_ref_narratives_user
                ON reference_narratives (user_id);
            """)

            # Scored narratives — every narrative that passes through run_score gets indexed here
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS scored_narratives (
                    id             BIGSERIAL PRIMARY KEY,
                    user_id        INTEGER   NOT NULL,
                    unique_id      TEXT      NOT NULL,
                    narrative_text TEXT      NOT NULL,
                    embedding      VECTOR({configured_dimension}) NOT NULL,
                    scored_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (user_id, unique_id)
                );
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_scored_narratives_user
                ON scored_narratives (user_id);
            """)
            cur.execute("""
                INSERT INTO vector_store_config (id, embedding_backend, embedding_model_id, embedding_dim)
                VALUES (1, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET embedding_backend  = EXCLUDED.embedding_backend,
                    embedding_model_id = EXCLUDED.embedding_model_id,
                    embedding_dim      = EXCLUDED.embedding_dim,
                    updated_at         = NOW();
            """, (configured_backend, configured_model_id, configured_dimension))
        conn.commit()


def upsert_reference_narratives(
    *,
    file_id: int,
    user_id: int,
    records: list[dict],
    embeddings: list[list[float]],
) -> None:
    """Store reference narratives with their embeddings."""
    if len(records) != len(embeddings):
        raise ValueError("records and embeddings length mismatch.")

    with _connect() as conn:
        with conn.cursor() as cur:
            # Remove existing narratives for this file_id to allow re-ingest
            cur.execute("DELETE FROM reference_narratives WHERE file_id = %s;", (file_id,))
            for record, vector in zip(records, embeddings):
                cur.execute(
                    """
                    INSERT INTO reference_narratives
                        (file_id, user_id, unique_id, narrative_text, content, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s::vector);
                    """,
                    (
                        file_id,
                        user_id,
                        record["unique_id"],
                        record["narrative_text"],
                        record["content"],
                        _ensure_vector_literal(vector),
                    ),
                )
        conn.commit()


def query_similar_references(
    *,
    user_id: int,
    query_embedding: list[float],
    limit: int = 5,
) -> list[ReferenceMatch]:
    """Find the most similar reference narratives for a given query embedding."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT unique_id, narrative_text, content,
                       1 - (embedding <=> %s::vector) AS score
                FROM reference_narratives
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
            rows = cur.fetchall()

    return [
        ReferenceMatch(
            unique_id=row[0],
            narrative_text=row[1],
            content=row[2],
            score=float(row[3]),
        )
        for row in rows
    ]


def upsert_scored_narrative(
    *,
    user_id: int,
    unique_id: str,
    narrative_text: str,
    embedding: list[float],
) -> None:
    """Index a scored narrative into pgvector so it is searchable from chat."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO scored_narratives (user_id, unique_id, narrative_text, embedding)
                VALUES (%s, %s, %s, %s::vector)
                ON CONFLICT (user_id, unique_id) DO UPDATE
                SET narrative_text = EXCLUDED.narrative_text,
                    embedding      = EXCLUDED.embedding,
                    scored_at      = NOW();
                """,
                (user_id, unique_id, narrative_text, _ensure_vector_literal(embedding)),
            )
        conn.commit()


def query_all_narratives(
    *,
    user_id: int,
    query_embedding: list[float],
    limit: int = 6,
) -> list[ReferenceMatch]:
    """Search both reference_narratives and scored_narratives, return top matches."""
    vec = _ensure_vector_literal(query_embedding)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT unique_id, narrative_text, narrative_text AS content,
                       1 - (embedding <=> %s::vector) AS score,
                       'reference' AS source
                FROM reference_narratives
                WHERE user_id = %s

                UNION ALL

                SELECT unique_id, narrative_text, narrative_text AS content,
                       1 - (embedding <=> %s::vector) AS score,
                       'scored' AS source
                FROM scored_narratives
                WHERE user_id = %s

                ORDER BY score DESC
                LIMIT %s;
                """,
                (vec, user_id, vec, user_id, limit),
            )
            rows = cur.fetchall()

    seen: set[str] = set()
    results: list[ReferenceMatch] = []
    for row in rows:
        uid = row[0]
        if uid in seen:
            continue
        seen.add(uid)
        results.append(ReferenceMatch(
            unique_id=uid,
            narrative_text=row[1],
            content=row[2],
            score=float(row[3]),
        ))
    return results[:limit]


def get_available_periods(user_id: int) -> list[str]:
    """Return sorted list of period tags (e.g. ['P-06', 'P-07']) found in unique_ids for this user."""
    import re
    _PERIOD_RE = re.compile(r"\bP[-–]?(\d{2})\b", re.IGNORECASE)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT unique_id FROM reference_narratives WHERE user_id = %s
                UNION
                SELECT DISTINCT unique_id FROM scored_narratives WHERE user_id = %s;
                """,
                (user_id, user_id),
            )
            rows = cur.fetchall()
    periods: set[str] = set()
    for (uid,) in rows:
        for m in _PERIOD_RE.finditer(uid or ""):
            periods.add(f"P-{m.group(1).zfill(2)}")
    return sorted(periods)


def delete_reference_file_vectors(file_id: int) -> None:
    """Remove all vectors for a given reference file."""
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM reference_narratives WHERE file_id = %s;", (file_id,))
        conn.commit()


def vector_store_status() -> dict[str, Any]:
    config = embedding_configuration()
    return {
        "configured": bool(PGVECTOR_DSN),
        "embedding_dim": int(config["dimension"]),
        "embedding_backend": str(config["backend"]),
        "embedding_model_id": str(config["model_id"]),
    }


def _get_existing_dimension(cur, table: str = "reference_narratives") -> int | None:
    row = cur.execute(
        """
        SELECT format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = %s
          AND a.attname = 'embedding'
          AND n.nspname = current_schema();
        """,
        (table,),
    ).fetchone()
    if not row or not row[0]:
        return None
    formatted = str(row[0])
    if not formatted.startswith("vector(") or not formatted.endswith(")"):
        return None
    return int(formatted.removeprefix("vector(").removesuffix(")"))


def _reset_schema(cur) -> None:
    cur.execute("DROP TABLE IF EXISTS reference_narratives;")
    cur.execute("DROP TABLE IF EXISTS scored_narratives;")
    cur.execute("DELETE FROM vector_store_config WHERE id = 1;")