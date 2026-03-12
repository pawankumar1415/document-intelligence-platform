from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.app.models.schemas import (
    ArtifactRecord,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
    AuthUserProfile,
    EmbeddingConfigUpdateRequest,
    EmbeddingCatalog,
    GeneratePptxRequest,
    GenerateResult,
    GenerateSowRequest,
    ParseResponse,
    ProviderCatalogResponse,
    ProjectCreateRequest,
    ProjectResponse,
    VectorStatusResponse,
)
from backend.app.services import persistence
from backend.app.services.auth_service import (
    create_user,
    create_user_session,
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
from backend.app.services.ppt_generator import PptGenerator
from backend.app.services.provider_catalog import get_provider_catalog, resolve_chat_model
from backend.app.services.sow_generator import SowGenerator
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


def get_required_user(authorization: str | None = Header(default=None)) -> dict:
    return require_authenticated_user(authorization)


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
        user=AuthUserProfile(id=int(user["id"]), email=user["email"]),
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
        user=AuthUserProfile(id=int(user["id"]), email=user["email"]),
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
        project_id=int(resolved_project_id),
        document_id=int(document_id),
    )


@router.post("/api/v1/generate/sow", response_model=GenerateResult)
def generate_sow(
    request: GenerateSowRequest,
    user: dict = Depends(get_required_user),
) -> GenerateResult:
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
