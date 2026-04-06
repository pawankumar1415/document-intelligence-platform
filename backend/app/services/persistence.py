from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DB_PATH = DATA_DIR / "app.db"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                word_count INTEGER NOT NULL,
                paragraph_count INTEGER NOT NULL,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                artifact_type TEXT NOT NULL,
                artifact_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                download_url TEXT NOT NULL,
                summary TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                project_id INTEGER,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS rubrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS rubric_criteria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rubric_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'medium' CHECK(severity IN ('low', 'medium', 'high')),
                sort_order INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(rubric_id) REFERENCES rubrics(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS validation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                rubric_id INTEGER NOT NULL,
                document_name TEXT NOT NULL,
                overall_verdict TEXT NOT NULL CHECK(overall_verdict IN ('PASS', 'PASS_WITH_WARNINGS', 'FAIL', 'ERROR')),
                compliance_score REAL NOT NULL DEFAULT 0,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(rubric_id) REFERENCES rubrics(id) ON DELETE CASCADE
            );
            """
        )
        # Migration: add is_admin column to existing databases that predate this column
        try:
            connection.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        # Migration: add is_active column
        try:
            connection.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # Column already exists


def create_user(email: str, password_hash: str, password_salt: str) -> dict[str, Any]:
    now = utc_now_iso()
    clean_email = email.lower().strip()
    try:
        with get_connection() as connection:
            # First registered user becomes admin
            existing_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            is_admin = 1 if existing_count == 0 else 0
            cursor = connection.execute(
                """
                INSERT INTO users (email, password_hash, password_salt, created_at, is_admin, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (clean_email, password_hash, password_salt, now, is_admin),
            )
            user_id = int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        raise ValueError("A user with this email already exists.") from exc

    return {"id": user_id, "email": clean_email, "created_at": now, "is_admin": bool(is_admin), "is_active": True}


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, email, password_hash, password_salt, created_at, is_admin, is_active FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()

    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, email, created_at, is_admin, is_active FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def create_session(token: str, user_id: int, expires_at: str) -> None:
    now = utc_now_iso()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO sessions (token, user_id, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, expires_at, now),
        )


def get_user_by_session_token(token: str) -> dict[str, Any] | None:
    now = utc_now_iso()
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT u.id, u.email, u.is_admin, u.is_active
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ? AND s.expires_at > ?
            """,
            (token, now),
        ).fetchone()

    return dict(row) if row else None


def create_project(user_id: int, name: str) -> dict[str, Any]:
    now = utc_now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO projects (user_id, name, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, name.strip(), now, now),
        )
        project_id = int(cursor.lastrowid)

    return {"id": project_id, "name": name.strip(), "created_at": now, "updated_at": now}


def get_project(project_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, user_id, name, created_at, updated_at
            FROM projects
            WHERE id = ?
            """,
            (project_id,),
        ).fetchone()
    return dict(row) if row else None


def list_projects(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, created_at, updated_at
            FROM projects
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def save_parsed_document(user_id: int, project_id: int, document_payload: dict[str, Any]) -> int:
    now = utc_now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO documents (
                project_id, user_id, filename, file_type, title, text, word_count, paragraph_count, raw_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                user_id,
                document_payload["filename"],
                document_payload["file_type"],
                document_payload["title"],
                document_payload["text"],
                int(document_payload["word_count"]),
                int(document_payload["paragraph_count"]),
                json.dumps(document_payload),
                now,
            ),
        )
        connection.execute(
            "UPDATE projects SET updated_at = ? WHERE id = ?",
            (now, project_id),
        )
        return int(cursor.lastrowid)


def save_artifact(user_id: int, project_id: int, artifact_payload: dict[str, Any]) -> int:
    now = utc_now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO artifacts (
                project_id, user_id, artifact_type, artifact_name, file_path, download_url, summary, raw_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                user_id,
                artifact_payload["artifact_type"],
                artifact_payload["artifact_name"],
                artifact_payload["file_path"],
                artifact_payload["download_url"],
                artifact_payload["summary"],
                json.dumps(artifact_payload),
                now,
            ),
        )
        connection.execute(
            "UPDATE projects SET updated_at = ? WHERE id = ?",
            (now, project_id),
        )
        return int(cursor.lastrowid)


def list_artifacts(user_id: int, project_id: int | None = None) -> list[dict[str, Any]]:
    with get_connection() as connection:
        if project_id is None:
            rows = connection.execute(
                """
                SELECT id, project_id, artifact_type, artifact_name, download_url, summary, created_at
                FROM artifacts
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, project_id, artifact_type, artifact_name, download_url, summary, created_at
                FROM artifacts
                WHERE user_id = ? AND project_id = ?
                ORDER BY created_at DESC
                """,
                (user_id, project_id),
            ).fetchall()

    return [dict(row) for row in rows]


def get_artifact_by_name(user_id: int, artifact_name: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, project_id, artifact_type, artifact_name, download_url, summary, created_at, file_path
            FROM artifacts
            WHERE user_id = ? AND artifact_name = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id, artifact_name),
        ).fetchone()
    return dict(row) if row else None


# ── Admin functions ────────────────────────────────────────────────────────────

def list_all_users() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, email, created_at, is_admin, is_active FROM users ORDER BY created_at ASC"
        ).fetchall()
    return [dict(row) for row in rows]


def update_user_flags(user_id: int, is_admin: bool | None = None, is_active: bool | None = None) -> bool:
    """Update is_admin and/or is_active flags. Returns True if row was updated."""
    if is_admin is None and is_active is None:
        return False
    parts: list[str] = []
    params: list[Any] = []
    if is_admin is not None:
        parts.append("is_admin = ?")
        params.append(1 if is_admin else 0)
    if is_active is not None:
        parts.append("is_active = ?")
        params.append(1 if is_active else 0)
    params.append(user_id)
    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE users SET {', '.join(parts)} WHERE id = ?", params
        )
    return cursor.rowcount > 0


def delete_user_by_id(user_id: int) -> bool:
    """Delete a user and all their data (cascades). Returns True if row was deleted."""
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
    return cursor.rowcount > 0


# ── Chat session functions ─────────────────────────────────────────────────────

def create_chat_session(user_id: int, project_id: int | None = None, metadata: dict | None = None) -> str:
    import uuid
    session_id = str(uuid.uuid4())
    now = utc_now_iso()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO chat_sessions (session_id, user_id, project_id, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, project_id, json.dumps(metadata or {}), now, now),
        )
    return session_id


def chat_session_exists(session_id: str) -> bool:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT 1 FROM chat_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    return row is not None


def load_chat_history(session_id: str, max_messages: int = 20) -> list[dict[str, Any]]:
    """Return last max_messages messages ordered oldest-first (suitable for LLM context)."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT role, content FROM (
                SELECT role, content, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ) ORDER BY created_at ASC
            """,
            (session_id, max_messages),
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def save_chat_turn(
    session_id: str,
    user_message: str,
    assistant_message: str,
    metadata: dict | None = None,
) -> None:
    """Persist a user/assistant exchange atomically."""
    now = utc_now_iso()
    meta_json = json.dumps(metadata or {})
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO chat_messages (session_id, role, content, metadata, created_at) VALUES (?, 'user', ?, ?, ?)",
            (session_id, user_message, meta_json, now),
        )
        connection.execute(
            "INSERT INTO chat_messages (session_id, role, content, metadata, created_at) VALUES (?, 'assistant', ?, ?, ?)",
            (session_id, assistant_message, meta_json, now),
        )
        connection.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ?",
            (now, session_id),
        )


# ── Rubric functions ───────────────────────────────────────────────────────────

_DEFAULT_RUBRIC_CRITERIA = [
    ("Clear Purpose & Objectives", "The document clearly states its purpose and what it aims to achieve.", "high", 0),
    ("Defined Scope", "The scope of work, coverage, or applicability is explicitly defined.", "high", 1),
    ("Structured & Logical Flow", "Content is organised logically with clear headings and a coherent narrative.", "medium", 2),
    ("Specific & Measurable Content", "Claims, deliverables, or outcomes are specific, measurable, and not vague.", "high", 3),
    ("Risks or Dependencies Identified", "Key risks, assumptions, or dependencies are acknowledged.", "medium", 4),
    ("Action Items & Ownership", "Any required actions are clearly assigned or attributed.", "medium", 5),
    ("Professional Language", "Language is professional, consistent, and free of unexplained jargon or acronyms.", "low", 6),
    ("Internal Consistency", "Figures, dates, and facts stated are internally consistent throughout the document.", "high", 7),
    ("Appropriate for Intended Audience", "The tone, detail level, and terminology suit the intended readership.", "low", 8),
]


def ensure_default_rubric(user_id: int) -> int:
    """Create the default General Document Quality rubric for a user if it doesn't exist. Returns rubric_id."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id FROM rubrics WHERE user_id = ? AND is_default = 1 LIMIT 1",
            (user_id,),
        ).fetchone()
        if row:
            return int(row["id"])

        now = utc_now_iso()
        cursor = connection.execute(
            """
            INSERT INTO rubrics (user_id, name, description, is_default, created_at, updated_at)
            VALUES (?, 'General Document Quality', 'A general-purpose rubric for assessing the quality and completeness of professional documents.', 1, ?, ?)
            """,
            (user_id, now, now),
        )
        rubric_id = int(cursor.lastrowid)
        for name, desc, severity, order in _DEFAULT_RUBRIC_CRITERIA:
            connection.execute(
                "INSERT INTO rubric_criteria (rubric_id, name, description, severity, sort_order) VALUES (?, ?, ?, ?, ?)",
                (rubric_id, name, desc, severity, order),
            )
        return rubric_id


def list_rubrics(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, description, is_default, created_at, updated_at FROM rubrics WHERE user_id = ? ORDER BY is_default DESC, name ASC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_rubric(rubric_id: int, user_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, name, description, is_default, created_at, updated_at FROM rubrics WHERE id = ? AND user_id = ?",
            (rubric_id, user_id),
        ).fetchone()
        if not row:
            return None
        rubric = dict(row)
        criteria_rows = connection.execute(
            "SELECT id, name, description, severity, sort_order FROM rubric_criteria WHERE rubric_id = ? ORDER BY sort_order ASC",
            (rubric_id,),
        ).fetchall()
        rubric["criteria"] = [dict(c) for c in criteria_rows]
    return rubric


def create_rubric(user_id: int, name: str, description: str, criteria: list[dict]) -> dict[str, Any]:
    now = utc_now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO rubrics (user_id, name, description, is_default, created_at, updated_at) VALUES (?, ?, ?, 0, ?, ?)",
            (user_id, name.strip(), description.strip(), now, now),
        )
        rubric_id = int(cursor.lastrowid)
        for i, criterion in enumerate(criteria):
            connection.execute(
                "INSERT INTO rubric_criteria (rubric_id, name, description, severity, sort_order) VALUES (?, ?, ?, ?, ?)",
                (rubric_id, criterion["name"], criterion.get("description", ""), criterion.get("severity", "medium"), i),
            )
    return get_rubric(rubric_id, user_id)  # type: ignore[return-value]


def delete_rubric(rubric_id: int, user_id: int) -> bool:
    with get_connection() as connection:
        row = connection.execute("SELECT is_default FROM rubrics WHERE id = ? AND user_id = ?", (rubric_id, user_id)).fetchone()
        if not row or row["is_default"]:
            return False  # Cannot delete the default rubric
        cursor = connection.execute("DELETE FROM rubrics WHERE id = ? AND user_id = ?", (rubric_id, user_id))
    return cursor.rowcount > 0


def save_validation_result(user_id: int, rubric_id: int, document_name: str, verdict: str, score: float, result: dict) -> int:
    now = utc_now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO validation_results (user_id, rubric_id, document_name, overall_verdict, compliance_score, result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, rubric_id, document_name, verdict, score, json.dumps(result), now),
        )
    return int(cursor.lastrowid)
