routes = """

# ── Template Library ──────────────────────────────────────────────────────────

from backend.app.models.schemas import (
    GenerationTemplateSummary, GenerationTemplateRecord, GenerationTemplateCreateRequest,
    ArtifactFeedbackRequest, ArtifactFeedbackRecord,
    ShareLinkCreateRequest, ShareLinkRecord,
    ProjectOverview,
)

@router.get("/api/v1/templates", response_model=list[GenerationTemplateSummary])
def list_templates(
    template_type: str | None = None,
    user: dict = Depends(get_required_user),
) -> list[GenerationTemplateSummary]:
    rows = persistence.list_templates(int(user["id"]), template_type)
    import json as _json
    return [GenerationTemplateSummary(
        id=r["id"], name=r["name"], description=r["description"],
        template_type=r["template_type"], is_default=bool(r["is_default"]),
        created_at=r["created_at"],
    ) for r in rows]


@router.get("/api/v1/templates/{template_id}", response_model=GenerationTemplateRecord)
def get_template(template_id: int, user: dict = Depends(get_required_user)) -> GenerationTemplateRecord:
    import json as _json
    row = persistence.get_template(template_id, int(user["id"]))
    if not row:
        raise HTTPException(status_code=404, detail="Template not found.")
    return GenerationTemplateRecord(
        id=row["id"], name=row["name"], description=row["description"],
        template_type=row["template_type"], is_default=bool(row["is_default"]),
        created_at=row["created_at"], config=_json.loads(row["config_json"] or "{}"),
    )


@router.post("/api/v1/templates", response_model=GenerationTemplateRecord)
def create_template(
    request: GenerationTemplateCreateRequest,
    user: dict = Depends(get_required_user),
) -> GenerationTemplateRecord:
    import json as _json
    row = persistence.create_template(
        user_id=int(user["id"]), name=request.name, description=request.description,
        template_type=request.template_type, config=request.config,
    )
    return GenerationTemplateRecord(
        id=row["id"], name=row["name"], description=row["description"],
        template_type=row["template_type"], is_default=False,
        created_at=row["created_at"], config=_json.loads(row["config_json"] or "{}"),
    )


@router.delete("/api/v1/templates/{template_id}", status_code=204)
def delete_template(template_id: int, user: dict = Depends(get_required_user)) -> None:
    deleted = persistence.delete_template(template_id, int(user["id"]))
    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found or is a built-in template.")


# ── Artifact Feedback ─────────────────────────────────────────────────────────

@router.post("/api/v1/artifacts/{artifact_id}/feedback", response_model=ArtifactFeedbackRecord)
def submit_feedback(
    artifact_id: int,
    request: ArtifactFeedbackRequest,
    user: dict = Depends(get_required_user),
) -> ArtifactFeedbackRecord:
    artifact = persistence.get_artifact_by_id(artifact_id, int(user["id"]))
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    row = persistence.save_feedback(
        artifact_id=artifact_id, user_id=int(user["id"]),
        section_title=request.section_title, rating=request.rating, note=request.note,
    )
    return ArtifactFeedbackRecord(**row)


@router.get("/api/v1/artifacts/{artifact_id}/feedback", response_model=list[ArtifactFeedbackRecord])
def get_feedback(artifact_id: int, user: dict = Depends(get_required_user)) -> list[ArtifactFeedbackRecord]:
    rows = persistence.list_feedback(artifact_id, int(user["id"]))
    return [ArtifactFeedbackRecord(**r) for r in rows]


# ── Share Links ───────────────────────────────────────────────────────────────

@router.post("/api/v1/artifacts/{artifact_id}/share", response_model=ShareLinkRecord)
def create_share_link(
    artifact_id: int,
    request: ShareLinkCreateRequest,
    user: dict = Depends(get_required_user),
) -> ShareLinkRecord:
    from datetime import datetime, timezone, timedelta
    import json as _json
    artifact = persistence.get_artifact_by_id(artifact_id, int(user["id"]))
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    expires_at = None
    if request.expires_in_days:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)).isoformat()
    row = persistence.create_share_link(artifact_id, int(user["id"]), expires_at)
    return ShareLinkRecord(
        token=row["token"], artifact_id=artifact_id,
        artifact_name=artifact["artifact_name"], artifact_type=artifact["artifact_type"],
        download_url=artifact["download_url"], summary=artifact["summary"],
        created_at=row["created_at"], expires_at=row["expires_at"],
    )


@router.get("/api/v1/artifacts/{artifact_id}/share", response_model=list[ShareLinkRecord])
def list_share_links(artifact_id: int, user: dict = Depends(get_required_user)) -> list[ShareLinkRecord]:
    rows = persistence.list_share_links(artifact_id, int(user["id"]))
    return [ShareLinkRecord(
        token=r["token"], artifact_id=r["artifact_id"],
        artifact_name=r["artifact_name"], artifact_type=r["artifact_type"],
        download_url=r["download_url"], summary=r["summary"],
        created_at=r["created_at"], expires_at=r.get("expires_at"),
    ) for r in rows]


@router.delete("/api/v1/share/{token}", status_code=204)
def revoke_share_link(token: str, user: dict = Depends(get_required_user)) -> None:
    persistence.delete_share_link(token, int(user["id"]))


# Public — no auth required
@router.get("/api/v1/share/{token}", response_model=ShareLinkRecord)
def get_shared_artifact(token: str) -> ShareLinkRecord:
    row = persistence.get_share_link(token)
    if not row:
        raise HTTPException(status_code=404, detail="Share link not found or has expired.")
    return ShareLinkRecord(
        token=row["token"], artifact_id=row["artifact_id"],
        artifact_name=row["artifact_name"], artifact_type=row["artifact_type"],
        download_url=row["download_url"], summary=row["summary"],
        created_at=row["created_at"], expires_at=row.get("expires_at"),
    )


# ── Project Overview ──────────────────────────────────────────────────────────

@router.get("/api/v1/projects/{project_id}/overview", response_model=ProjectOverview)
def get_project_overview(project_id: int, user: dict = Depends(get_required_user)) -> ProjectOverview:
    overview = persistence.get_project_overview(project_id, int(user["id"]))
    if not overview:
        raise HTTPException(status_code=404, detail="Project not found.")
    return ProjectOverview(**overview)
"""

path = "d:/Projects/Document Intelligence Platform/backend/app/api/routes.py"
with open(path, "a", encoding="utf-8") as f:
    f.write(routes)
print("done")