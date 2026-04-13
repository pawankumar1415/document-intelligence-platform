from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.app.models.schemas import (
    AdminUserRecord,
    AdminUserUpdateRequest,
    AnalyticsDashboard,
    ArtifactRecord,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
    AuthUserProfile,
    AuthUserProfileExtended,
    BatchValidateRequest,
    BatchValidateResponse,
    ChatRequest,
    ChatResponse,
    ChatMeta,
    ClauseAutoExtractRequest,
    ClauseCreateRequest,
    ClauseRecord,
    ClauseSearchResponse,
    CompareRequest,
    ComparisonResult,
    EmbeddingConfigUpdateRequest,
    EmbeddingCatalog,
    ExtractRequest,
    ExtractionResult,
    ExtractionSchemaCreateRequest,
    ExtractionSchemaRecord,
    ExtractionSchemaSummary,
    CaseStudyMetric,
    GenerateBidRequest,
    GenerateCaseStudyRequest,
    GeneratePptxRequest,
    GenerateResult,
    GenerateSowRequest,
    ParseResponse,
    ProviderCatalogResponse,
    ProjectCreateRequest,
    ProjectResponse,
    RubricCreateRequest,
    RubricRecord,
    RubricSummary,
    SharePointDownloadRequest,
    SharePointFile,
    SharePointFilesResponse,
    SharePointLibrary,
    SharePointSite,
    SummarizeRequest,
    SummarizeResponse,
    SummaryGroup,
    SummaryInsight,
    UseCaseAssessment,
    ValidateRequest,
    ValidationResult,
    VectorStatusResponse,
)
from backend.app.services import persistence
from backend.app.services.auth_service import (
    create_user,
    create_user_session,
    require_admin_user,
    require_authenticated_user,
    verify_credentials,
)
from backend.app.services.chunking import chunk_text
from backend.app.services.embedding_service import (
    embed_documents,
    embed_query,
    embedding_configuration,
    get_runtime_embedding_override,
    set_runtime_embedding_config,
    set_runtime_embedding_override,
)
from backend.app.services.file_utils import OUTPUT_DIR
from backend.app.services.document_parser import DocumentParser
from backend.app.services.bid_generator import BidGenerator
from backend.app.services.case_study_generator import CaseStudyGenerator
from backend.app.services.ppt_generator import PptGenerator
from backend.app.services.provider_catalog import get_provider_catalog, resolve_chat_model
from backend.app.services.summarization_service import summarize_document
from backend.app.services.sow_generator import SowGenerator
from backend.app.services.use_case_router import screen_document_for_supported_use_cases
from backend.app.services.vector_store import (
    init_vector_store,
    query_similar_chunks,
    upsert_chunks,
    vector_store_status,
)


router = APIRouter()

document_parser = DocumentParser()
sow_generator = SowGenerator()
ppt_generator = PptGenerator()
bid_generator = BidGenerator()
case_study_generator = CaseStudyGenerator()


def get_required_user(authorization: str | None = Header(default=None)) -> dict:
    return require_authenticated_user(authorization)


def get_admin_user(authorization: str | None = Header(default=None)) -> dict:
    return require_admin_user(authorization)


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/v1/vector/status", response_model=VectorStatusResponse)
def get_vector_status() -> VectorStatusResponse:
    status = vector_store_status()
    return VectorStatusResponse(**status)


@router.get("/api/v1/providers/models", response_model=ProviderCatalogResponse)
def get_provider_models(user: dict = Depends(get_required_user)) -> ProviderCatalogResponse:
    del user
    return ProviderCatalogResponse(
        providers=get_provider_catalog(),
        embedding=embedding_configuration(),
    )


@router.post("/api/v1/summarize", response_model=SummarizeResponse)
def summarize(
    request: SummarizeRequest,
    user: dict = Depends(get_required_user),
) -> SummarizeResponse:
    del user
    try:
        return summarize_document(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {exc}") from exc


@router.post("/api/v1/embedding/config", response_model=EmbeddingCatalog)
def update_embedding_config(
    request: EmbeddingConfigUpdateRequest,
    user: dict = Depends(get_required_user),
) -> EmbeddingCatalog:
    del user
    previous_backend, previous_model = get_runtime_embedding_override()
    try:
        set_runtime_embedding_config(backend=request.backend, model_id=request.model_id)
        init_vector_store()
    except Exception as exc:
        set_runtime_embedding_override(previous_backend, previous_model)
        raise HTTPException(status_code=400, detail=f"Embedding config update failed: {exc}") from exc
    return EmbeddingCatalog(**embedding_configuration())


@router.post("/api/v1/auth/register", response_model=AuthResponse)
def register_user(request: AuthRegisterRequest) -> AuthResponse:
    try:
        user = create_user(email=request.email, password=request.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    token, ttl_seconds = create_user_session(user_id=int(user["id"]))
    return AuthResponse(
        access_token=token,
        expires_in_seconds=ttl_seconds,
        user=AuthUserProfileExtended(
            id=int(user["id"]),
            email=user["email"],
            is_admin=bool(user.get("is_admin", False)),
            is_active=bool(user.get("is_active", True)),
        ),
    )


@router.post("/api/v1/auth/login", response_model=AuthResponse)
def login_user(request: AuthLoginRequest) -> AuthResponse:
    user = verify_credentials(email=request.email, password=request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token, ttl_seconds = create_user_session(user_id=int(user["id"]))
    return AuthResponse(
        access_token=token,
        expires_in_seconds=ttl_seconds,
        user=AuthUserProfileExtended(
            id=int(user["id"]),
            email=user["email"],
            is_admin=bool(user.get("is_admin", False)),
            is_active=bool(user.get("is_active", True)),
        ),
    )


@router.post("/api/v1/projects", response_model=ProjectResponse)
def create_project(
    request: ProjectCreateRequest,
    user: dict = Depends(get_required_user),
) -> ProjectResponse:
    project = persistence.create_project(user_id=int(user["id"]), name=request.name)
    return ProjectResponse(
        id=int(project["id"]),
        name=project["name"],
        created_at=project["created_at"],
        updated_at=project["updated_at"],
    )


@router.get("/api/v1/projects", response_model=list[ProjectResponse])
def list_projects(user: dict = Depends(get_required_user)) -> list[ProjectResponse]:
    projects = persistence.list_projects(user_id=int(user["id"]))
    return [
        ProjectResponse(
            id=int(project["id"]),
            name=project["name"],
            created_at=project["created_at"],
            updated_at=project["updated_at"],
        )
        for project in projects
    ]


@router.post("/api/v1/parse", response_model=ParseResponse)
async def parse_document(
    file: UploadFile = File(...),
    project_id: int | None = Form(default=None),
    project_name: str | None = Form(default=None),
    llm_provider: str = Form(default="openai"),
    user: dict = Depends(get_required_user),
) -> ParseResponse:
    try:
        parsed_document = await document_parser.parse_upload(file)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    use_case_screening = screen_document_for_supported_use_cases(parsed_document)
    use_case_assessment = UseCaseAssessment(
        is_supported=use_case_screening.is_supported,
        matched_use_cases=use_case_screening.matched_use_cases,
        confidence=use_case_screening.confidence,
        reasons=use_case_screening.reasons,
    )
    if not use_case_screening.is_supported:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "unsupported_document",
                "message": "This document does not match supported use cases for this platform.",
                "assessment": use_case_assessment.model_dump(),
            },
        )

    user_id = int(user["id"])
    resolved_project_id = project_id

    if resolved_project_id is not None:
        project = persistence.get_project(resolved_project_id)
        if not project or int(project["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Project not found for this user.")
    else:
        inferred_name = (project_name or parsed_document.title or "Untitled Project").strip()
        project = persistence.create_project(user_id=user_id, name=inferred_name)
        resolved_project_id = int(project["id"])

    document_id = persistence.save_parsed_document(
        user_id=user_id,
        project_id=int(resolved_project_id),
        document_payload=parsed_document.model_dump(),
    )

    chunks = chunk_text(parsed_document.text)
    if not chunks:
        chunks = [parsed_document.text]
    try:
        embeddings = embed_documents(chunks)
        upsert_chunks(
            user_id=user_id,
            project_id=int(resolved_project_id),
            source_id=f"document:{document_id}",
            provider=llm_provider,
            chunks=chunks,
            embeddings=embeddings,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Vector indexing failed: {exc}") from exc

    return ParseResponse(
        document=parsed_document,
        use_case_assessment=use_case_assessment,
        project_id=int(resolved_project_id),
        document_id=int(document_id),
    )


@router.post("/api/v1/generate/sow", response_model=GenerateResult)
def generate_sow(
    request: GenerateSowRequest,
    user: dict = Depends(get_required_user),
) -> GenerateResult:
    use_case_screening = screen_document_for_supported_use_cases(request.source_document)
    if not use_case_screening.is_supported:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "unsupported_document",
                "message": "This document does not match supported generation use cases.",
                "assessment": UseCaseAssessment(
                    is_supported=use_case_screening.is_supported,
                    matched_use_cases=use_case_screening.matched_use_cases,
                    confidence=use_case_screening.confidence,
                    reasons=use_case_screening.reasons,
                ).model_dump(),
            },
        )

    user_id = int(user["id"])
    resolved_project_id = request.project_id
    if resolved_project_id is not None:
        project = persistence.get_project(resolved_project_id)
        if not project or int(project["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Project not found for this user.")
    else:
        project = persistence.create_project(user_id=user_id, name=request.project_name)
        resolved_project_id = int(project["id"])

    retrieval_context: list[str] = []
    try:
        request.llm_model = resolve_chat_model(request.llm_provider, request.llm_model)
        query_embedding = embed_query(request.source_document.text[:1500])
        matches = query_similar_chunks(
            user_id=user_id,
            project_id=int(resolved_project_id),
            query_embedding=query_embedding,
            limit=5,
        )
        retrieval_context = [match.content for match in matches]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        retrieval_context = []

    result = sow_generator.generate(request, retrieval_context=retrieval_context)
    artifact_id = persistence.save_artifact(
        user_id=user_id,
        project_id=int(resolved_project_id),
        artifact_payload=result.model_dump(),
    )
    result.project_id = int(resolved_project_id)
    result.artifact_id = int(artifact_id)
    return result


@router.post("/api/v1/generate/pptx", response_model=GenerateResult)
def generate_pptx(
    request: GeneratePptxRequest,
    user: dict = Depends(get_required_user),
) -> GenerateResult:
    use_case_screening = screen_document_for_supported_use_cases(request.source_document)
    if not use_case_screening.is_supported:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "unsupported_document",
                "message": "This document does not match supported generation use cases.",
                "assessment": UseCaseAssessment(
                    is_supported=use_case_screening.is_supported,
                    matched_use_cases=use_case_screening.matched_use_cases,
                    confidence=use_case_screening.confidence,
                    reasons=use_case_screening.reasons,
                ).model_dump(),
            },
        )

    user_id = int(user["id"])
    resolved_project_id = request.project_id
    if resolved_project_id is not None:
        project = persistence.get_project(resolved_project_id)
        if not project or int(project["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Project not found for this user.")
    else:
        project = persistence.create_project(user_id=user_id, name=request.deck_title)
        resolved_project_id = int(project["id"])

    retrieval_context: list[str] = []
    try:
        request.llm_model = resolve_chat_model(request.llm_provider, request.llm_model)
        query_embedding = embed_query(request.source_document.text[:1500])
        matches = query_similar_chunks(
            user_id=user_id,
            project_id=int(resolved_project_id),
            query_embedding=query_embedding,
            limit=5,
        )
        retrieval_context = [match.content for match in matches]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        retrieval_context = []

    result = ppt_generator.generate(request, retrieval_context=retrieval_context)
    artifact_id = persistence.save_artifact(
        user_id=user_id,
        project_id=int(resolved_project_id),
        artifact_payload=result.model_dump(),
    )
    result.project_id = int(resolved_project_id)
    result.artifact_id = int(artifact_id)
    return result


@router.get("/api/v1/artifacts", response_model=list[ArtifactRecord])
def list_artifacts(
    project_id: int | None = None,
    user: dict = Depends(get_required_user),
) -> list[ArtifactRecord]:
    if project_id is not None:
        project = persistence.get_project(project_id)
        if not project or int(project["user_id"]) != int(user["id"]):
            raise HTTPException(status_code=403, detail="Project not found for this user.")

    records = persistence.list_artifacts(user_id=int(user["id"]), project_id=project_id)
    return [ArtifactRecord(**record) for record in records]


@router.get("/api/v1/artifacts/{artifact_name}")
def download_artifact(
    artifact_name: str,
    user: dict = Depends(get_required_user),
) -> FileResponse:
    artifact_record = persistence.get_artifact_by_name(int(user["id"]), artifact_name)
    if not artifact_record:
        raise HTTPException(status_code=404, detail="Artifact not found for this user.")

    safe_name = Path(artifact_name).name
    artifact_path = OUTPUT_DIR / safe_name

    if not artifact_path.exists() or not artifact_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found.")

    return FileResponse(
        path=artifact_path,
        filename=safe_name,
        media_type="application/octet-stream",
    )


# ── Chat endpoint ──────────────────────────────────────────────────────────────

@router.post("/api/v1/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    user: dict = Depends(get_required_user),
) -> ChatResponse:
    from backend.app.services.chat_service import run_chat

    try:
        result = run_chat(
            question=request.question,
            user_id=int(user["id"]),
            session_id=request.session_id,
            project_id=request.project_id,
            provider=request.llm_provider,
            model=request.llm_model,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        answer=result["answer"],
        session_id=result["session_id"],
        meta=ChatMeta(**result["meta"]),
    )


# ── Admin endpoints ────────────────────────────────────────────────────────────

@router.get("/api/v1/admin/users", response_model=list[AdminUserRecord])
def admin_list_users(admin: dict = Depends(get_admin_user)) -> list[AdminUserRecord]:
    del admin
    users = persistence.list_all_users()
    return [
        AdminUserRecord(
            id=int(u["id"]),
            email=u["email"],
            created_at=u["created_at"],
            is_admin=bool(u["is_admin"]),
            is_active=bool(u["is_active"]),
        )
        for u in users
    ]


@router.patch("/api/v1/admin/users/{user_id}", response_model=AdminUserRecord)
def admin_update_user(
    user_id: int,
    request: AdminUserUpdateRequest,
    admin: dict = Depends(get_admin_user),
) -> AdminUserRecord:
    del admin
    updated = persistence.update_user_flags(
        user_id=user_id,
        is_admin=request.is_admin,
        is_active=request.is_active,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found.")
    user = persistence.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return AdminUserRecord(
        id=int(user["id"]),
        email=user["email"],
        created_at=user["created_at"],
        is_admin=bool(user["is_admin"]),
        is_active=bool(user["is_active"]),
    )


@router.delete("/api/v1/admin/users/{user_id}", status_code=204)
def admin_delete_user(
    user_id: int,
    admin: dict = Depends(get_admin_user),
) -> None:
    if int(admin["id"]) == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")
    deleted = persistence.delete_user_by_id(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found.")


# ── Rubric endpoints ───────────────────────────────────────────────────────────

@router.get("/api/v1/rubrics", response_model=list[RubricSummary])
def list_rubrics(user: dict = Depends(get_required_user)) -> list[RubricSummary]:
    user_id = int(user["id"])
    persistence.ensure_default_rubric(user_id)
    rubrics = persistence.list_rubrics(user_id)
    return [RubricSummary(**r) for r in rubrics]


@router.get("/api/v1/rubrics/{rubric_id}", response_model=RubricRecord)
def get_rubric(rubric_id: int, user: dict = Depends(get_required_user)) -> RubricRecord:
    rubric = persistence.get_rubric(rubric_id, int(user["id"]))
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found.")
    return RubricRecord(**rubric)


@router.post("/api/v1/rubrics", response_model=RubricRecord, status_code=201)
def create_rubric_endpoint(request: RubricCreateRequest, user: dict = Depends(get_required_user)) -> RubricRecord:
    rubric = persistence.create_rubric(
        user_id=int(user["id"]),
        name=request.name,
        description=request.description,
        criteria=[c.model_dump() for c in request.criteria],
    )
    return RubricRecord(**rubric)


@router.delete("/api/v1/rubrics/{rubric_id}", status_code=204)
def delete_rubric_endpoint(rubric_id: int, user: dict = Depends(get_required_user)) -> None:
    deleted = persistence.delete_rubric(rubric_id, int(user["id"]))
    if not deleted:
        raise HTTPException(status_code=404, detail="Rubric not found or cannot delete the default rubric.")


# ── Validation endpoints ───────────────────────────────────────────────────────

@router.post("/api/v1/validate", response_model=ValidationResult)
def validate_document(
    request: ValidateRequest,
    user: dict = Depends(get_required_user),
) -> ValidationResult:
    from backend.app.services.validation_service import run_validation
    try:
        result = run_validation(
            text=request.text,
            document_name=request.document_name,
            user_id=int(user["id"]),
            rubric_id=request.rubric_id,
            provider=request.llm_provider,
            model=request.llm_model,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ValidationResult(**result)


@router.post("/api/v1/validate/batch", response_model=BatchValidateResponse)
async def validate_batch(
    rubric_id: int | None = Form(default=None),
    llm_provider: str = Form(default="openai"),
    llm_model: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    user: dict = Depends(get_required_user),
) -> BatchValidateResponse:
    from backend.app.services.excel_parser import parse_csv_for_batch, parse_excel_for_batch
    from backend.app.services.validation_service import run_batch_validation

    items: list[dict] = []

    if file and file.filename:
        raw_bytes = await file.read()
        filename_lower = (file.filename or "").lower()
        try:
            if filename_lower.endswith((".xlsx", ".xls")):
                items = parse_excel_for_batch(raw_bytes, filename=file.filename or "")
            elif filename_lower.endswith(".csv"):
                items = parse_csv_for_batch(raw_bytes)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type. Upload .xlsx, .xls, or .csv")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not items:
        raise HTTPException(status_code=400, detail="No documents found in the uploaded file.")

    try:
        result = run_batch_validation(
            items=items,
            user_id=int(user["id"]),
            rubric_id=rubric_id,
            provider=llm_provider,  # type: ignore[arg-type]
            model=llm_model,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return BatchValidateResponse(**result)


# ── SharePoint endpoints ───────────────────────────────────────────────────────

@router.get("/api/v1/sharepoint/status")
def sharepoint_status(user: dict = Depends(get_required_user)) -> dict:
    del user
    from backend.app.services.sharepoint_service import is_configured
    return {"configured": is_configured()}


@router.get("/api/v1/sharepoint/sites", response_model=list[SharePointSite])
def get_sharepoint_sites(user: dict = Depends(get_required_user)) -> list[SharePointSite]:
    del user
    from backend.app.services.sharepoint_service import list_sites
    try:
        sites = list_sites()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return [SharePointSite(**s) for s in sites]


@router.get("/api/v1/sharepoint/libraries", response_model=list[SharePointLibrary])
def get_sharepoint_libraries(
    site_id: str | None = None,
    user: dict = Depends(get_required_user),
) -> list[SharePointLibrary]:
    del user
    from backend.app.services.sharepoint_service import list_libraries
    try:
        libraries = list_libraries(site_id=site_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return [SharePointLibrary(**lib) for lib in libraries]


@router.get("/api/v1/sharepoint/files", response_model=SharePointFilesResponse)
def get_sharepoint_files(
    library_id: str,
    folder_path: str = "/",
    user: dict = Depends(get_required_user),
) -> SharePointFilesResponse:
    del user
    from backend.app.services.sharepoint_service import list_files
    try:
        items = list_files(library_id=library_id, folder_path=folder_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return SharePointFilesResponse(
        library_id=library_id,
        folder_path=folder_path,
        items=[SharePointFile(**item) for item in items],
    )


@router.post("/api/v1/sharepoint/download-and-parse", response_model=ParseResponse)
async def sharepoint_download_and_parse(
    request: SharePointDownloadRequest,
    llm_provider: str = "openai",
    project_id: int | None = None,
    user: dict = Depends(get_required_user),
) -> ParseResponse:
    import io
    from backend.app.services.sharepoint_service import download_file
    from fastapi import UploadFile as FU

    try:
        file_bytes = download_file(library_id=request.library_id, item_id=request.item_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    upload = FU(filename=request.filename, file=io.BytesIO(file_bytes))

    try:
        parsed_document = await document_parser.parse_upload(upload)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    use_case_screening = screen_document_for_supported_use_cases(parsed_document)
    use_case_assessment = UseCaseAssessment(
        is_supported=use_case_screening.is_supported,
        matched_use_cases=use_case_screening.matched_use_cases,
        confidence=use_case_screening.confidence,
        reasons=use_case_screening.reasons,
    )
    if not use_case_screening.is_supported:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "unsupported_document",
                "message": "This document does not match supported use cases.",
                "assessment": use_case_assessment.model_dump(),
            },
        )

    user_id = int(user["id"])
    resolved_project_id = project_id
    if resolved_project_id is not None:
        project = persistence.get_project(resolved_project_id)
        if not project or int(project["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Project not found for this user.")
    else:
        project = persistence.create_project(user_id=user_id, name=parsed_document.title or request.filename)
        resolved_project_id = int(project["id"])

    document_id = persistence.save_parsed_document(
        user_id=user_id,
        project_id=int(resolved_project_id),
        document_payload=parsed_document.model_dump(),
    )

    chunks = chunk_text(parsed_document.text) or [parsed_document.text]
    try:
        embeddings = embed_documents(chunks)
        upsert_chunks(
            user_id=user_id,
            project_id=int(resolved_project_id),
            source_id=f"document:{document_id}",
            provider=llm_provider,
            chunks=chunks,
            embeddings=embeddings,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Vector indexing failed: {exc}") from exc

    return ParseResponse(
        document=parsed_document,
        use_case_assessment=use_case_assessment,
        project_id=int(resolved_project_id),
        document_id=int(document_id),
    )


# ── Bid generation endpoint ────────────────────────────────────────────────────

@router.post("/api/v1/generate/bid", response_model=GenerateResult)
def generate_bid(
    request: GenerateBidRequest,
    user: dict = Depends(get_required_user),
) -> GenerateResult:
    user_id = int(user["id"])
    resolved_project_id = request.project_id
    if resolved_project_id is not None:
        project = persistence.get_project(resolved_project_id)
        if not project or int(project["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Project not found for this user.")
    else:
        project = persistence.create_project(user_id=user_id, name=request.opportunity_title)
        resolved_project_id = int(project["id"])

    retrieval_context: list[str] = []
    try:
        request.llm_model = resolve_chat_model(request.llm_provider, request.llm_model)
        query_embedding = embed_query(request.source_document.text[:1500])
        matches = query_similar_chunks(
            user_id=user_id,
            project_id=int(resolved_project_id),
            query_embedding=query_embedding,
            limit=5,
        )
        retrieval_context = [match.content for match in matches]
    except Exception:
        retrieval_context = []

    result = bid_generator.generate(request, retrieval_context=retrieval_context)
    artifact_id = persistence.save_artifact(
        user_id=user_id,
        project_id=int(resolved_project_id),
        artifact_payload=result.model_dump(),
    )
    result.project_id = int(resolved_project_id)
    result.artifact_id = int(artifact_id)
    return result


# ── Comparison endpoint ────────────────────────────────────────────────────────

@router.post("/api/v1/compare", response_model=ComparisonResult)
def compare_documents_endpoint(
    request: CompareRequest,
    user: dict = Depends(get_required_user),
) -> ComparisonResult:
    from backend.app.services.comparison_service import compare_documents
    del user
    try:
        return compare_documents(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {exc}") from exc


# ── Extraction schema endpoints ────────────────────────────────────────────────

@router.get("/api/v1/extraction-schemas", response_model=list[ExtractionSchemaSummary])
def list_extraction_schemas_endpoint(user: dict = Depends(get_required_user)) -> list[ExtractionSchemaSummary]:
    user_id = int(user["id"])
    persistence.ensure_default_extraction_schemas(user_id)
    schemas = persistence.list_extraction_schemas(user_id)
    return [ExtractionSchemaSummary(**{k: v for k, v in s.items() if k != "fields"}) for s in schemas]


@router.get("/api/v1/extraction-schemas/{schema_id}", response_model=ExtractionSchemaRecord)
def get_extraction_schema_endpoint(schema_id: int, user: dict = Depends(get_required_user)) -> ExtractionSchemaRecord:
    schema = persistence.get_extraction_schema(schema_id, int(user["id"]))
    if not schema:
        raise HTTPException(status_code=404, detail="Extraction schema not found.")
    return ExtractionSchemaRecord(**schema)


@router.post("/api/v1/extraction-schemas", response_model=ExtractionSchemaRecord, status_code=201)
def create_extraction_schema_endpoint(
    request: ExtractionSchemaCreateRequest,
    user: dict = Depends(get_required_user),
) -> ExtractionSchemaRecord:
    schema = persistence.create_extraction_schema(
        user_id=int(user["id"]),
        name=request.name,
        description=request.description,
        entity_label=request.entity_label,
        fields=[f.model_dump() for f in request.fields],
    )
    return ExtractionSchemaRecord(**schema)


@router.delete("/api/v1/extraction-schemas/{schema_id}", status_code=204)
def delete_extraction_schema_endpoint(schema_id: int, user: dict = Depends(get_required_user)) -> None:
    deleted = persistence.delete_extraction_schema(schema_id, int(user["id"]))
    if not deleted:
        raise HTTPException(status_code=404, detail="Schema not found or cannot delete a built-in schema.")


@router.post("/api/v1/extract", response_model=ExtractionResult)
def extract_structured_data(
    request: ExtractRequest,
    user: dict = Depends(get_required_user),
) -> ExtractionResult:
    from backend.app.services.extractor_service import run_extraction
    user_id = int(user["id"])
    try:
        result = run_extraction(request, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}") from exc

    if request.project_id:
        project = persistence.get_project(request.project_id)
        if project and int(project["user_id"]) == user_id:
            persistence.save_artifact(
                user_id=user_id,
                project_id=request.project_id,
                artifact_payload={
                    "artifact_type": "register",
                    "file_path": str(OUTPUT_DIR / result.artifact_name),
                    "artifact_name": result.artifact_name,
                    "download_url": result.download_url,
                    "summary": f"{result.schema_name} register — {result.total_extracted} {result.entity_label} entries",
                    "sections": [],
                    "slides": [],
                },
            )
    return result


# ── Analytics endpoint ─────────────────────────────────────────────────────────

@router.get("/api/v1/analytics", response_model=AnalyticsDashboard)
def get_analytics(user: dict = Depends(get_required_user)) -> AnalyticsDashboard:
    from backend.app.services.analytics_service import get_dashboard
    return get_dashboard(user_id=int(user["id"]))


# ── Clause library endpoints ───────────────────────────────────────────────────

@router.get("/api/v1/clauses", response_model=list[ClauseRecord])
def list_clauses(
    project_id: int | None = None,
    user: dict = Depends(get_required_user),
) -> list[ClauseRecord]:
    records = persistence.list_clauses(user_id=int(user["id"]), project_id=project_id)
    return [ClauseRecord(**{**r, "tags": r.get("tags", [])}) for r in records]


@router.post("/api/v1/clauses", response_model=ClauseRecord, status_code=201)
def create_clause(
    request: ClauseCreateRequest,
    user: dict = Depends(get_required_user),
) -> ClauseRecord:
    from backend.app.services.clause_service import save_clause_and_index
    return save_clause_and_index(
        user_id=int(user["id"]),
        project_id=request.project_id,
        title=request.title,
        content=request.content,
        tags=request.tags,
        source_doc=request.source_doc,
    )


@router.delete("/api/v1/clauses/{clause_id}", status_code=204)
def delete_clause(clause_id: int, user: dict = Depends(get_required_user)) -> None:
    deleted = persistence.delete_clause(clause_id, int(user["id"]))
    if not deleted:
        raise HTTPException(status_code=404, detail="Clause not found.")


@router.get("/api/v1/clauses/search", response_model=ClauseSearchResponse)
def search_clauses(
    q: str,
    user: dict = Depends(get_required_user),
) -> ClauseSearchResponse:
    from backend.app.services.clause_service import search_clauses_semantic
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")
    results = search_clauses_semantic(user_id=int(user["id"]), query=q.strip(), limit=10)
    return ClauseSearchResponse(query=q, results=results)


@router.post("/api/v1/clauses/auto-extract", response_model=list[ClauseRecord])
def auto_extract_clauses(
    request: ClauseAutoExtractRequest,
    user: dict = Depends(get_required_user),
) -> list[ClauseRecord]:
    from backend.app.services.clause_service import auto_extract_clauses as _auto_extract
    try:
        return _auto_extract(
            text=request.text,
            doc_name=request.document_name,
            user_id=int(user["id"]),
            project_id=request.project_id,
            provider=request.llm_provider,
            model=request.llm_model,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Auto-extraction failed: {exc}") from exc


@router.post("/api/v1/generate/case-study", response_model=GenerateResult)
def generate_case_study(
    request: GenerateCaseStudyRequest,
    user: dict = Depends(get_required_user),
) -> GenerateResult:
    try:
        result = case_study_generator.generate(request)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Case study generation failed: {exc}") from exc
