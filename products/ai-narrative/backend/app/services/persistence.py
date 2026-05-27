"""
persistence.py — SQLite data access layer for AI Narrative Search.

Tables:
  users           — authentication credentials
  sessions        — bearer tokens (8-hour TTL)
  admin_flags     — is_admin / is_active per user
  rubrics         — custom scoring rubrics
  reference_files — uploaded reference Excel files (metadata)
  score_results   — narrative scoring history
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from backend.app.config import env

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[3] / "data" / "narrative.db"
DB_PATH: Path = Path(env("SQLITE_DB_PATH") or str(_DEFAULT_DB_PATH))
DATA_DIR: Path = DB_PATH.parent


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                password_salt TEXT    NOT NULL,
                created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admin_flags (
                user_id   INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                is_admin  INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS rubrics (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name          TEXT    NOT NULL,
                description   TEXT    NOT NULL DEFAULT '',
                is_default    INTEGER NOT NULL DEFAULT 0,
                criteria_json TEXT    NOT NULL DEFAULT '[]',
                created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS reference_files (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                filename     TEXT    NOT NULL,
                description  TEXT    NOT NULL DEFAULT '',
                record_count INTEGER NOT NULL DEFAULT 0,
                indexed_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS score_results (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                unique_id        TEXT    NOT NULL,
                document_name    TEXT    NOT NULL,
                overall_verdict  TEXT    NOT NULL,
                compliance_score REAL    NOT NULL DEFAULT 0,
                raw_json         TEXT    NOT NULL DEFAULT '{}',
                created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS domain_profiles (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                profile_json TEXT    NOT NULL DEFAULT '{}',
                confidence   REAL    NOT NULL DEFAULT 0.0,
                updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                user_id          INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                active_rubric_id INTEGER REFERENCES rubrics(id) ON DELETE SET NULL,
                updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS financial_uploads (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                filename     TEXT    NOT NULL,
                record_count INTEGER NOT NULL DEFAULT 0,
                uploaded_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS financial_records (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id INTEGER NOT NULL REFERENCES financial_uploads(id) ON DELETE CASCADE,
                user_id   INTEGER NOT NULL,
                unique_id TEXT    NOT NULL,
                raw_data  TEXT    NOT NULL DEFAULT '{}',
                UNIQUE(user_id, unique_id)
            );

            CREATE TABLE IF NOT EXISTS score_audit (
                id                       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id                  INTEGER NOT NULL,
                unique_id                TEXT    NOT NULL,
                provider                 TEXT    NOT NULL DEFAULT '',
                model_name               TEXT    NOT NULL DEFAULT '',
                prompt_hash              TEXT    NOT NULL DEFAULT '',
                compliance_score         REAL,
                layer2_abnormality_count INTEGER,
                layer3_discrepancy_count INTEGER,
                verdict                  TEXT,
                has_custom_rules         INTEGER NOT NULL DEFAULT 0,
                has_financial_data       INTEGER NOT NULL DEFAULT 0,
                scored_at                TEXT    NOT NULL DEFAULT (datetime('now'))
            );
        """)
        # Migrations for older schemas
        try:
            conn.execute(
                "ALTER TABLE users ADD COLUMN onboarding_completed INTEGER NOT NULL DEFAULT 0"
            )
        except Exception:
            pass
        # Indexes for new tables (safe to run repeatedly)
        for stmt in (
            "CREATE INDEX IF NOT EXISTS idx_financial_records_user_uid ON financial_records(user_id, unique_id);",
            "CREATE INDEX IF NOT EXISTS idx_score_audit_user_date ON score_audit(user_id, scored_at);",
        ):
            try:
                conn.execute(stmt)
            except Exception:
                pass


# ── Users ─────────────────────────────────────────────────────────────────────

def create_user(*, email: str, password_hash: str, password_salt: str) -> dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, password_salt) VALUES (?, ?, ?)",
            (email.lower().strip(), password_hash, password_salt),
        )
        user_id = cursor.lastrowid
        # First user is admin
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        is_admin = 1 if user_count == 1 else 0
        conn.execute(
            "INSERT INTO admin_flags (user_id, is_admin, is_active) VALUES (?, ?, 1)",
            (user_id, is_admin),
        )
    return {"id": user_id, "email": email, "is_admin": bool(is_admin), "is_active": True}


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.email, u.password_hash, u.password_salt,
                   COALESCE(a.is_admin, 0)  AS is_admin,
                   COALESCE(a.is_active, 1) AS is_active,
                   COALESCE(u.onboarding_completed, 0) AS onboarding_completed
            FROM users u
            LEFT JOIN admin_flags a ON a.user_id = u.id
            WHERE u.email = ?
            """,
            (email.lower().strip(),),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_session_token(token: str) -> dict[str, Any] | None:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.email,
                   COALESCE(a.is_admin, 0)  AS is_admin,
                   COALESCE(a.is_active, 1) AS is_active,
                   COALESCE(u.onboarding_completed, 0) AS onboarding_completed
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            LEFT JOIN admin_flags a ON a.user_id = u.id
            WHERE s.token = ? AND s.expires_at > ?
            """,
            (token, now),
        ).fetchone()
    return dict(row) if row else None


def create_session(*, token: str, user_id: int, expires_at: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at),
        )


def list_all_users() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.email, u.created_at,
                   COALESCE(a.is_admin, 0)  AS is_admin,
                   COALESCE(a.is_active, 1) AS is_active,
                   COUNT(DISTINCT s.id)     AS score_count
            FROM users u
            LEFT JOIN admin_flags a ON a.user_id = u.id
            LEFT JOIN score_results s ON s.user_id = u.id
            GROUP BY u.id
            ORDER BY u.created_at DESC
            """,
        ).fetchall()
    return [dict(r) for r in rows]


def update_admin_flags(user_id: int, *, is_admin: bool | None, is_active: bool | None) -> None:
    with get_connection() as conn:
        if is_admin is not None:
            conn.execute(
                "UPDATE admin_flags SET is_admin = ? WHERE user_id = ?",
                (int(is_admin), user_id),
            )
        if is_active is not None:
            conn.execute(
                "UPDATE admin_flags SET is_active = ? WHERE user_id = ?",
                (int(is_active), user_id),
            )


def delete_user(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


# ── Rubrics ───────────────────────────────────────────────────────────────────

_DEFAULT_RUBRIC_CRITERIA = [
    {"name": "Clarity", "description": "The narrative is clearly written and easy to understand.", "severity": "high"},
    {"name": "Completeness", "description": "All required information is present with no gaps.", "severity": "high"},
    {"name": "Accuracy", "description": "Figures and claims match supporting data.", "severity": "high"},
    {"name": "Structure", "description": "The narrative follows a logical, coherent structure.", "severity": "medium"},
    {"name": "Professional Tone", "description": "Language is appropriate for an executive/external audience.", "severity": "medium"},
    {"name": "No Jargon/Acronyms", "description": "All acronyms are expanded on first use; no unexplained jargon.", "severity": "low"},
    {"name": "Consistent Dates", "description": "All dates are in the correct format and consistent throughout.", "severity": "low"},
]


def ensure_default_rubric(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM rubrics WHERE user_id = ? AND is_default = 1 LIMIT 1",
            (user_id,),
        ).fetchone()
        if row:
            return int(row["id"])
        cursor = conn.execute(
            """
            INSERT INTO rubrics (user_id, name, description, is_default, criteria_json)
            VALUES (?, ?, ?, 1, ?)
            """,
            (
                user_id,
                "Default Narrative Rubric",
                "Standard quality criteria for narrative text.",
                json.dumps(_DEFAULT_RUBRIC_CRITERIA),
            ),
        )
        return cursor.lastrowid


def get_rubric(rubric_id: int, user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM rubrics WHERE id = ? AND user_id = ?",
            (rubric_id, user_id),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["criteria"] = json.loads(d.get("criteria_json") or "[]")
    return d


def list_rubrics(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, description, is_default, criteria_json FROM rubrics WHERE user_id = ? ORDER BY is_default DESC, id",
            (user_id,),
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        criteria = json.loads(d.pop("criteria_json", "[]"))
        d["criteria_count"] = len(criteria)
        result.append(d)
    return result


def create_rubric(*, user_id: int, name: str, description: str, criteria: list[dict]) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO rubrics (user_id, name, description, criteria_json) VALUES (?, ?, ?, ?)",
            (user_id, name, description, json.dumps(criteria)),
        )
        return cursor.lastrowid


def delete_rubric(rubric_id: int, user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM rubrics WHERE id = ? AND user_id = ? AND is_default = 0",
            (rubric_id, user_id),
        )


# ── Reference Files ───────────────────────────────────────────────────────────

def save_reference_file(*, user_id: int, filename: str, description: str, record_count: int) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO reference_files (user_id, filename, description, record_count) VALUES (?, ?, ?, ?)",
            (user_id, filename, description, record_count),
        )
        return cursor.lastrowid


def list_reference_files(user_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, filename, description, record_count, indexed_at FROM reference_files WHERE user_id = ? ORDER BY indexed_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_reference_file(file_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM reference_files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        )
        return cursor.rowcount > 0


def get_reference_file(file_id: int, user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM reference_files WHERE id = ? AND user_id = ?",
            (file_id, user_id),
        ).fetchone()
    return dict(row) if row else None


# ── Score Results ─────────────────────────────────────────────────────────────

def save_score_result(
    *,
    user_id: int,
    unique_id: str,
    document_name: str,
    overall_verdict: str,
    compliance_score: float,
    result: dict[str, Any],
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO score_results (user_id, unique_id, document_name, overall_verdict, compliance_score, raw_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, unique_id, document_name, overall_verdict, compliance_score, json.dumps(result)),
        )
        return cursor.lastrowid


def list_score_results(user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, unique_id, document_name, overall_verdict, compliance_score, created_at
            FROM score_results WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_score_result(result_id: int, user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM score_results WHERE id = ? AND user_id = ?",
            (result_id, user_id),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["result"] = json.loads(d.get("raw_json") or "{}")
    return d


# ── Domain Profiles ───────────────────────────────────────────────────────────

def save_domain_profile(user_id: int, profile: dict, confidence: float) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO domain_profiles (user_id, profile_json, confidence, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE
            SET profile_json = excluded.profile_json,
                confidence   = excluded.confidence,
                updated_at   = datetime('now')
            """,
            (user_id, json.dumps(profile), confidence),
        )


def get_domain_profile(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT profile_json, confidence, updated_at FROM domain_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row:
        return None
    profile = json.loads(row["profile_json"] or "{}")
    profile["confidence"] = row["confidence"]
    profile["updated_at"] = row["updated_at"]
    return profile


def delete_domain_profile(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM domain_profiles WHERE user_id = ?", (user_id,))


def complete_onboarding(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET onboarding_completed = 1 WHERE id = ?",
            (user_id,),
        )


# ── User Settings (custom rules rubric override) ──────────────────────────────

def get_active_rules_rubric_id(user_id: int) -> int | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT active_rubric_id FROM user_settings WHERE user_id = ?", (user_id,)
        ).fetchone()
    return int(row["active_rubric_id"]) if row and row["active_rubric_id"] else None


def set_active_rules_rubric(user_id: int, rubric_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_settings (user_id, active_rubric_id, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE
            SET active_rubric_id = excluded.active_rubric_id,
                updated_at       = datetime('now')
            """,
            (user_id, rubric_id),
        )


def clear_active_rules_rubric(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE user_settings SET active_rubric_id = NULL, updated_at = datetime('now') WHERE user_id = ?",
            (user_id,),
        )


# ── Financial Uploads ──────────────────────────────────────────────────────────

def save_financial_upload(*, user_id: int, filename: str, records: list[dict]) -> int:
    """Replace any existing financial upload for this user and store new records."""
    with get_connection() as conn:
        # Delete old upload (cascades to financial_records)
        conn.execute("DELETE FROM financial_uploads WHERE user_id = ?", (user_id,))
        cursor = conn.execute(
            "INSERT INTO financial_uploads (user_id, filename, record_count) VALUES (?, ?, ?)",
            (user_id, filename, len(records)),
        )
        upload_id = cursor.lastrowid
        for rec in records:
            conn.execute(
                """
                INSERT INTO financial_records (upload_id, user_id, unique_id, raw_data)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, unique_id) DO UPDATE
                SET raw_data  = excluded.raw_data,
                    upload_id = excluded.upload_id
                """,
                (upload_id, user_id, rec["unique_id"], json.dumps(rec["raw_data"])),
            )
    return upload_id


def get_financial_upload_status(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, filename, record_count, uploaded_at FROM financial_uploads WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_financial_upload(user_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM financial_uploads WHERE user_id = ?", (user_id,))


def get_financial_record(*, user_id: int, unique_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        # Exact match first
        row = conn.execute(
            "SELECT raw_data FROM financial_records WHERE user_id = ? AND unique_id = ?",
            (user_id, unique_id),
        ).fetchone()
        if not row:
            # Case-insensitive fallback
            row = conn.execute(
                "SELECT raw_data FROM financial_records WHERE user_id = ? AND lower(unique_id) = lower(?)",
                (user_id, unique_id),
            ).fetchone()
    return json.loads(row["raw_data"]) if row else None


# ── Score Audit ────────────────────────────────────────────────────────────────

def save_audit_entry(
    *,
    user_id: int,
    unique_id: str,
    provider: str,
    model_name: str,
    prompt_hash: str,
    compliance_score: float | None,
    layer2_abnormality_count: int | None,
    layer3_discrepancy_count: int | None,
    verdict: str | None,
    has_custom_rules: bool,
    has_financial_data: bool,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO score_audit (
                user_id, unique_id, provider, model_name, prompt_hash,
                compliance_score, layer2_abnormality_count, layer3_discrepancy_count,
                verdict, has_custom_rules, has_financial_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, unique_id, provider, model_name, prompt_hash,
                compliance_score, layer2_abnormality_count, layer3_discrepancy_count,
                verdict, int(has_custom_rules), int(has_financial_data),
            ),
        )


def get_audit_records(user_id: int, days: int = 30) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT unique_id, provider, model_name, prompt_hash,
                   compliance_score, layer2_abnormality_count, layer3_discrepancy_count,
                   verdict, has_custom_rules, has_financial_data, scored_at
            FROM score_audit
            WHERE user_id = ?
              AND scored_at >= datetime('now', ?)
            ORDER BY scored_at ASC
            """,
            (user_id, f"-{days} days"),
        ).fetchall()
    return [dict(r) for r in rows]


def purge_old_audit_records(user_id: int, days: int = 30) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM score_audit WHERE user_id = ? AND scored_at < datetime('now', ?)",
            (user_id, f"-{days} days"),
        )
    return cur.rowcount


def get_analytics_overview(user_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        counts = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN overall_verdict = 'PASS' THEN 1 ELSE 0 END) AS pass_count,
                SUM(CASE WHEN overall_verdict = 'PASS_WITH_WARNINGS' THEN 1 ELSE 0 END) AS warn_count,
                SUM(CASE WHEN overall_verdict = 'FAIL' THEN 1 ELSE 0 END) AS fail_count,
                AVG(compliance_score) AS avg_score
            FROM score_results WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        ref_count = conn.execute(
            "SELECT COUNT(*) FROM reference_files WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
    return {
        "total_scored": int(counts["total"] or 0),
        "pass_count": int(counts["pass_count"] or 0),
        "warn_count": int(counts["warn_count"] or 0),
        "fail_count": int(counts["fail_count"] or 0),
        "avg_compliance_score": round(float(counts["avg_score"] or 0.0), 2),
        "reference_files_count": int(ref_count or 0),
    }