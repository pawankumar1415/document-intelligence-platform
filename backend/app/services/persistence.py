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
                project_id INTEGER,
                document_name TEXT NOT NULL,
                overall_verdict TEXT NOT NULL CHECK(overall_verdict IN ('PASS', 'PASS_WITH_WARNINGS', 'FAIL', 'ERROR')),
                compliance_score REAL NOT NULL DEFAULT 0,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(rubric_id) REFERENCES rubrics(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS extraction_schemas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                entity_label TEXT NOT NULL,
                fields_json TEXT NOT NULL DEFAULT '[]',
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS clauses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                project_id INTEGER,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags_json TEXT NOT NULL DEFAULT '[]',
                source_doc TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS generation_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                template_type TEXT NOT NULL CHECK(template_type IN ('sow','pptx','bid','case_study')),
                config_json TEXT NOT NULL DEFAULT '{}',
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS artifact_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artifact_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                section_title TEXT NOT NULL DEFAULT '',
                rating INTEGER NOT NULL CHECK(rating IN (1, -1)),
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS share_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                artifact_id INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                expires_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE,
                FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        # Migration: add is_admin column to existing databases that predate this column
        try:
            connection.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            connection.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        except sqlite3.OperationalError:
            pass
        try:
            connection.execute("ALTER TABLE validation_results ADD COLUMN project_id INTEGER")
        except sqlite3.OperationalError:
            pass


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


def save_validation_result(user_id: int, rubric_id: int, document_name: str, verdict: str, score: float, result: dict, project_id: int | None = None) -> int:
    now = utc_now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO validation_results (user_id, rubric_id, project_id, document_name, overall_verdict, compliance_score, result_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, rubric_id, project_id, document_name, verdict, score, json.dumps(result), now),
        )
    return int(cursor.lastrowid)


def get_validation_by_id(validation_id: int, user_id: int) -> dict | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT vr.id, vr.document_name, vr.overall_verdict, vr.compliance_score,
                   vr.result_json, vr.created_at, r.name AS rubric_name
            FROM validation_results vr
            LEFT JOIN rubrics r ON r.id = vr.rubric_id
            WHERE vr.id = ? AND vr.user_id = ?
            """,
            (validation_id, user_id),
        ).fetchone()
    if not row:
        return None
    result = json.loads(row["result_json"])
    return {
        "id": row["id"],
        "document_name": row["document_name"],
        "overall_verdict": row["overall_verdict"],
        "compliance_score": float(row["compliance_score"]),
        "rubric_name": row["rubric_name"] or "",
        "created_at": row["created_at"],
        "layer1": result.get("layer1", {}),
        "layer2": result.get("layer2", {}),
        "rewritten_text": result.get("rewritten_text", ""),
        "meta": result.get("meta", {}),
    }


# ── Extraction schema functions ────────────────────────────────────────────────

_DEFAULT_EXTRACTION_SCHEMAS = [
    ("Risks & Mitigations", "Extract risks, their likelihood, impact, and mitigation actions.", "Risk",
     [{"name": "Risk Description", "description": "What could go wrong", "required": True},
      {"name": "Likelihood", "description": "H / M / L", "required": True},
      {"name": "Impact", "description": "H / M / L", "required": True},
      {"name": "Mitigation", "description": "How the risk is mitigated", "required": True},
      {"name": "Owner", "description": "Who owns the risk", "required": False}]),
    ("Requirements", "Extract functional or non-functional requirements.", "Requirement",
     [{"name": "ID", "description": "Requirement identifier e.g. REQ-001", "required": False},
      {"name": "Description", "description": "Full requirement statement", "required": True},
      {"name": "Priority", "description": "H / M / L or MoSCoW", "required": True},
      {"name": "Acceptance Criteria", "description": "How this will be verified", "required": False},
      {"name": "Status", "description": "Open / In Progress / Done", "required": False}]),
    ("Action Items", "Extract action items, owners, and due dates.", "Action Item",
     [{"name": "Action", "description": "What needs to be done", "required": True},
      {"name": "Owner", "description": "Who is responsible", "required": True},
      {"name": "Due Date", "description": "Target completion date", "required": False},
      {"name": "Priority", "description": "H / M / L", "required": False},
      {"name": "Status", "description": "Open / In Progress / Done", "required": False}]),
    ("Stakeholders", "Extract stakeholders, their roles, and responsibilities.", "Stakeholder",
     [{"name": "Name / Role", "description": "Person or role title", "required": True},
      {"name": "Responsibility", "description": "What they are responsible for", "required": True},
      {"name": "Influence", "description": "H / M / L", "required": False},
      {"name": "Engagement Level", "description": "Inform / Consult / Collaborate / Lead", "required": False}]),
    ("Decisions", "Extract decisions made, their rationale, and impact.", "Decision",
     [{"name": "Decision", "description": "What was decided", "required": True},
      {"name": "Rationale", "description": "Why this decision was made", "required": True},
      {"name": "Made By", "description": "Who made the decision", "required": False},
      {"name": "Date", "description": "When it was decided", "required": False},
      {"name": "Impact", "description": "Effect on the project or team", "required": False}]),
]


def ensure_default_extraction_schemas(user_id: int) -> None:
    """Create built-in extraction schemas for a user if they don't exist yet."""
    with get_connection() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM extraction_schemas WHERE user_id = ? AND is_default = 1",
            (user_id,),
        ).fetchone()[0]
        if count > 0:
            return
        now = utc_now_iso()
        for name, desc, entity_label, fields in _DEFAULT_EXTRACTION_SCHEMAS:
            connection.execute(
                """
                INSERT INTO extraction_schemas (user_id, name, description, entity_label, fields_json, is_default, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (user_id, name, desc, entity_label, json.dumps(fields), now, now),
            )


def list_extraction_schemas(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT id, name, description, entity_label, fields_json, is_default, created_at, updated_at FROM extraction_schemas WHERE user_id = ? ORDER BY is_default DESC, name ASC",
            (user_id,),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["fields"] = json.loads(d.pop("fields_json", "[]"))
        result.append(d)
    return result


def get_extraction_schema(schema_id: int, user_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, name, description, entity_label, fields_json, is_default, created_at, updated_at FROM extraction_schemas WHERE id = ? AND user_id = ?",
            (schema_id, user_id),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["fields"] = json.loads(d.pop("fields_json", "[]"))
    return d


def create_extraction_schema(user_id: int, name: str, description: str, entity_label: str, fields: list[dict]) -> dict[str, Any]:
    now = utc_now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO extraction_schemas (user_id, name, description, entity_label, fields_json, is_default, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
            (user_id, name.strip(), description.strip(), entity_label.strip(), json.dumps(fields), now, now),
        )
        schema_id = int(cursor.lastrowid)
    return get_extraction_schema(schema_id, user_id)  # type: ignore[return-value]


def delete_extraction_schema(schema_id: int, user_id: int) -> bool:
    with get_connection() as connection:
        row = connection.execute("SELECT is_default FROM extraction_schemas WHERE id = ? AND user_id = ?", (schema_id, user_id)).fetchone()
        if not row or row["is_default"]:
            return False
        cursor = connection.execute("DELETE FROM extraction_schemas WHERE id = ? AND user_id = ?", (schema_id, user_id))
    return cursor.rowcount > 0


# ── Clause functions ───────────────────────────────────────────────────────────

def save_clause(user_id: int, project_id: int | None, title: str, content: str, tags: list[str], source_doc: str) -> dict[str, Any]:
    now = utc_now_iso()
    with get_connection() as connection:
        cursor = connection.execute(
            "INSERT INTO clauses (user_id, project_id, title, content, tags_json, source_doc, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, project_id, title.strip(), content.strip(), json.dumps(tags), source_doc.strip(), now),
        )
        clause_id = int(cursor.lastrowid)
    return {"id": clause_id, "user_id": user_id, "project_id": project_id, "title": title.strip(), "content": content.strip(), "tags": tags, "source_doc": source_doc.strip(), "created_at": now}


def list_clauses(user_id: int, project_id: int | None = None) -> list[dict[str, Any]]:
    with get_connection() as connection:
        if project_id is not None:
            rows = connection.execute(
                "SELECT id, project_id, title, content, tags_json, source_doc, created_at FROM clauses WHERE user_id = ? AND project_id = ? ORDER BY created_at DESC",
                (user_id, project_id),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT id, project_id, title, content, tags_json, source_doc, created_at FROM clauses WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["tags"] = json.loads(d.pop("tags_json", "[]"))
        result.append(d)
    return result


def get_clause(clause_id: int, user_id: int) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, project_id, title, content, tags_json, source_doc, created_at FROM clauses WHERE id = ? AND user_id = ?",
            (clause_id, user_id),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["tags"] = json.loads(d.pop("tags_json", "[]"))
    return d


def delete_clause(clause_id: int, user_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM clauses WHERE id = ? AND user_id = ?", (clause_id, user_id))
    return cursor.rowcount > 0


def count_clauses(user_id: int) -> int:
    with get_connection() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM clauses WHERE user_id = ?", (user_id,)).fetchone()[0])


# ── Analytics functions ────────────────────────────────────────────────────────

def get_analytics_overview(user_id: int) -> dict[str, Any]:
    with get_connection() as connection:
        total_documents = connection.execute("SELECT COUNT(*) FROM documents WHERE user_id = ?", (user_id,)).fetchone()[0]
        total_artifacts = connection.execute("SELECT COUNT(*) FROM artifacts WHERE user_id = ?", (user_id,)).fetchone()[0]
        total_validations = connection.execute("SELECT COUNT(*) FROM validation_results WHERE user_id = ?", (user_id,)).fetchone()[0]
        total_clauses = connection.execute("SELECT COUNT(*) FROM clauses WHERE user_id = ?", (user_id,)).fetchone()[0]
        score_row = connection.execute(
            "SELECT AVG(compliance_score), COUNT(*) FROM validation_results WHERE user_id = ?", (user_id,)
        ).fetchone()
        avg_score = round(float(score_row[0] or 0), 2)
        pass_count = connection.execute(
            "SELECT COUNT(*) FROM validation_results WHERE user_id = ? AND overall_verdict IN ('PASS', 'PASS_WITH_WARNINGS')",
            (user_id,),
        ).fetchone()[0]
        pass_rate = round(pass_count / total_validations * 100, 1) if total_validations > 0 else 0.0
    return {
        "total_documents": int(total_documents),
        "total_artifacts": int(total_artifacts),
        "total_validations": int(total_validations),
        "avg_compliance_score": avg_score,
        "pass_rate": pass_rate,
        "total_clauses": int(total_clauses),
    }


def get_validation_trends(user_id: int, days: int = 30) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                substr(created_at, 1, 10) AS date,
                AVG(compliance_score) AS avg_score,
                COUNT(*) AS count,
                SUM(CASE WHEN overall_verdict IN ('PASS','PASS_WITH_WARNINGS') THEN 1 ELSE 0 END) AS pass_count
            FROM validation_results
            WHERE user_id = ?
              AND created_at >= datetime('now', ? || ' days')
            GROUP BY substr(created_at, 1, 10)
            ORDER BY date ASC
            """,
            (user_id, f"-{days}"),
        ).fetchall()
    return [{"date": row["date"], "avg_score": round(float(row["avg_score"]), 2), "count": int(row["count"]), "pass_count": int(row["pass_count"])} for row in rows]


def get_common_issues(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """Parse stored result_json to aggregate most frequent issue strings."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT result_json FROM validation_results WHERE user_id = ? ORDER BY created_at DESC LIMIT 200",
            (user_id,),
        ).fetchall()
    issue_counts: dict[str, int] = {}
    for row in rows:
        try:
            result = json.loads(row["result_json"])
            for issue in result.get("layer1", {}).get("issues", []):
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
            for issue in result.get("layer2", {}).get("consistency_issues", []):
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        except Exception:
            continue
    sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"issue": issue, "count": count} for issue, count in sorted_issues]


def get_recent_activity(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    with get_connection() as connection:
        doc_rows = connection.execute(
            "SELECT title AS name, created_at FROM documents WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        art_rows = connection.execute(
            "SELECT artifact_name AS name, artifact_type, created_at FROM artifacts WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        val_rows = connection.execute(
            "SELECT document_name AS name, overall_verdict, compliance_score, created_at FROM validation_results WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        clause_rows = connection.execute(
            "SELECT title AS name, created_at FROM clauses WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()

    activity: list[dict[str, Any]] = []
    for row in doc_rows:
        activity.append({"activity_type": "document", "name": row["name"], "created_at": row["created_at"], "details": "Parsed document"})
    for row in art_rows:
        activity.append({"activity_type": "artifact", "name": row["name"], "created_at": row["created_at"], "details": f"{row['artifact_type'].upper()} generated"})
    for row in val_rows:
        activity.append({"activity_type": "validation", "name": row["name"], "created_at": row["created_at"], "details": f"Verdict: {row['overall_verdict']} — Score: {row['compliance_score']:.1f}"})
    for row in clause_rows:
        activity.append({"activity_type": "clause", "name": row["name"], "created_at": row["created_at"], "details": "Saved to clause library"})

    activity.sort(key=lambda x: x["created_at"], reverse=True)
    return activity[:limit]


# ── Template Library CRUD ─────────────────────────────────────────────────────

def list_templates(user_id: int, template_type: str | None = None) -> list[dict]:
    _ensure_default_templates(user_id)
    with get_connection() as conn:
        if template_type:
            rows = conn.execute(
                "SELECT id,name,description,template_type,config_json,is_default,created_at FROM generation_templates WHERE user_id=? AND template_type=? ORDER BY is_default DESC, name",
                (user_id, template_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id,name,description,template_type,config_json,is_default,created_at FROM generation_templates WHERE user_id=? ORDER BY template_type, is_default DESC, name",
                (user_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def get_template(template_id: int, user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id,name,description,template_type,config_json,is_default,created_at FROM generation_templates WHERE id=? AND user_id=?",
            (template_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def create_template(user_id: int, name: str, description: str, template_type: str, config: dict) -> dict:
    now = utc_now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO generation_templates (user_id,name,description,template_type,config_json,is_default,created_at) VALUES (?,?,?,?,?,0,?)",
            (user_id, name.strip(), description.strip(), template_type, json.dumps(config), now),
        )
        tid = int(cursor.lastrowid)
    return {"id": tid, "name": name.strip(), "description": description.strip(), "template_type": template_type, "config_json": json.dumps(config), "is_default": 0, "created_at": now}


def delete_template(template_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        deleted = conn.execute(
            "DELETE FROM generation_templates WHERE id=? AND user_id=? AND is_default=0",
            (template_id, user_id),
        ).rowcount
    return deleted > 0


def _ensure_default_templates(user_id: int) -> None:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT COUNT(*) FROM generation_templates WHERE user_id=? AND is_default=1",
            (user_id,),
        ).fetchone()[0]
    if existing:
        return
    defaults = [
        ("Standard SOW", "Default Statement of Work template for consulting engagements.", "sow",
         {"tone": "formal", "assumptions": ["Client will provide named SMEs with adequate availability.", "All workshops will be conducted on client premises unless otherwise agreed.", "Sign-off will be provided within 5 business days of each deliverable."], "custom_instructions": ""}),
        ("Executive PPT Deck", "Concise deck for senior stakeholder presentations.", "pptx",
         {"max_slides": 8, "subtitle_template": "Prepared by BSBI Consulting", "tone": "executive"}),
        ("Bid Response — Consulting", "Standard proposal response for consulting opportunities.", "bid",
         {"our_strengths": ["Deep sector expertise across housing, healthcare and financial services.", "Proven delivery methodology with measurable outcomes.", "Flexible commercial model and dedicated UK-based team."], "tone": "confident"}),
        ("Case Study — Standard", "Standard case study for completed engagements.", "case_study",
         {"client_industry": "", "approach_points": [], "tone": "professional"}),
    ]
    now = utc_now_iso()
    with get_connection() as conn:
        for name, desc, ttype, config in defaults:
            conn.execute(
                "INSERT OR IGNORE INTO generation_templates (user_id,name,description,template_type,config_json,is_default,created_at) VALUES (?,?,?,?,?,1,?)",
                (user_id, name, desc, ttype, json.dumps(config), now),
            )


# ── Artifact Feedback CRUD ────────────────────────────────────────────────────

def save_feedback(artifact_id: int, user_id: int, section_title: str, rating: int, note: str) -> dict:
    now = utc_now_iso()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO artifact_feedback (artifact_id,user_id,section_title,rating,note,created_at) VALUES (?,?,?,?,?,?)",
            (artifact_id, user_id, section_title, rating, note, now),
        )
        fid = int(cursor.lastrowid)
    return {"id": fid, "artifact_id": artifact_id, "section_title": section_title, "rating": rating, "note": note, "created_at": now}


def list_feedback(artifact_id: int, user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id,artifact_id,section_title,rating,note,created_at FROM artifact_feedback WHERE artifact_id=? AND user_id=? ORDER BY created_at DESC",
            (artifact_id, user_id),
        ).fetchall()
    return [dict(r) for r in rows]


def get_artifact_by_id(artifact_id: int, user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id,project_id,artifact_type,artifact_name,download_url,summary,created_at FROM artifacts WHERE id=? AND user_id=?",
            (artifact_id, user_id),
        ).fetchone()
    return dict(row) if row else None


# ── Share Links CRUD ──────────────────────────────────────────────────────────

def create_share_link(artifact_id: int, user_id: int, expires_at: str | None) -> dict:
    import secrets
    token = secrets.token_urlsafe(32)
    now = utc_now_iso()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO share_links (token,artifact_id,created_by,expires_at,created_at) VALUES (?,?,?,?,?)",
            (token, artifact_id, user_id, expires_at, now),
        )
    return {"token": token, "artifact_id": artifact_id, "created_by": user_id, "expires_at": expires_at, "created_at": now}


def get_share_link(token: str) -> dict | None:
    now = utc_now_iso()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT sl.token, sl.artifact_id, sl.expires_at, sl.created_at,"
            " a.artifact_name, a.artifact_type, a.download_url, a.summary"
            " FROM share_links sl JOIN artifacts a ON a.id = sl.artifact_id"
            " WHERE sl.token=? AND (sl.expires_at IS NULL OR sl.expires_at > ?)",
            (token, now),
        ).fetchone()
    return dict(row) if row else None


def delete_share_link(token: str, user_id: int) -> bool:
    with get_connection() as conn:
        deleted = conn.execute(
            "DELETE FROM share_links WHERE token=? AND created_by=?",
            (token, user_id),
        ).rowcount
    return deleted > 0


def list_share_links(artifact_id: int, user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT sl.token, sl.artifact_id, sl.expires_at, sl.created_at,"
            " a.artifact_name, a.artifact_type, a.download_url, a.summary"
            " FROM share_links sl JOIN artifacts a ON a.id = sl.artifact_id"
            " WHERE sl.artifact_id=? AND sl.created_by=? ORDER BY sl.created_at DESC",
            (artifact_id, user_id),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Project Overview ──────────────────────────────────────────────────────────

def get_project_overview(project_id: int, user_id: int) -> dict | None:
    with get_connection() as conn:
        proj = conn.execute(
            "SELECT id, name, created_at, updated_at FROM projects WHERE id=? AND user_id=?",
            (project_id, user_id),
        ).fetchone()
        if not proj:
            return None
        docs = conn.execute(
            "SELECT id, filename, title, word_count, created_at FROM documents WHERE project_id=? AND user_id=? ORDER BY created_at DESC",
            (project_id, user_id),
        ).fetchall()
        arts = conn.execute(
            "SELECT id, artifact_type, artifact_name, download_url, summary, created_at FROM artifacts WHERE project_id=? AND user_id=? ORDER BY created_at DESC",
            (project_id, user_id),
        ).fetchall()
        vals = conn.execute(
            "SELECT id, document_name, overall_verdict, compliance_score, created_at FROM validation_results WHERE user_id=? AND project_id=? ORDER BY created_at DESC LIMIT 10",
            (user_id, project_id),
        ).fetchall()
        clause_count = conn.execute(
            "SELECT COUNT(*) FROM clauses WHERE project_id=? AND user_id=?",
            (project_id, user_id),
        ).fetchone()[0]
    return {
        "id": proj["id"],
        "name": proj["name"],
        "created_at": proj["created_at"],
        "updated_at": proj["updated_at"],
        "documents": [dict(d) for d in docs],
        "artifacts": [dict(a) for a in arts],
        "recent_validations": [dict(v) for v in vals],
        "clause_count": int(clause_count),
    }
