from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.app.models.schemas import (
    ArtifactRecord,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
    AuthUserProfile,
    GeneratePptxRequest,
    GenerateResult,
    GenerateSowRequest,
    ParseResponse,
    ProjectCreateRequest,
    ProjectResponse,
)
from backend.app.services import persistence
from backend.app.services.auth_service import (
    create_user,
    create_user_session,
    get_user_from_bearer_token,
    require_authenticated_user,
    verify_credentials,
)
from backend.app.services.file_utils import OUTPUT_DIR
from backend.app.services.document_parser import DocumentParser
from backend.app.services.ppt_generator import PptGenerator
from backend.app.services.sow_generator import SowGenerator


router = APIRouter()

document_parser = DocumentParser()
sow_generator = SowGenerator()
ppt_generator = PptGenerator()


def get_optional_user(authorization: str | None = Header(default=None)) -> dict | None:
    return get_user_from_bearer_token(authorization)


def get_required_user(authorization: str | None = Header(default=None)) -> dict:
    return require_authenticated_user(authorization)


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


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
    user: dict | None = Depends(get_optional_user),
) -> ParseResponse:
    try:
        parsed_document = await document_parser.parse_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    response = ParseResponse(document=parsed_document)

    if not user:
        return response

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
    response.project_id = int(resolved_project_id)
    response.document_id = int(document_id)
    return response


@router.post("/api/v1/generate/sow", response_model=GenerateResult)
def generate_sow(
    request: GenerateSowRequest,
    user: dict | None = Depends(get_optional_user),
) -> GenerateResult:
    result = sow_generator.generate(request)

    if not user:
        return result

    user_id = int(user["id"])
    resolved_project_id = request.project_id
    if resolved_project_id is not None:
        project = persistence.get_project(resolved_project_id)
        if not project or int(project["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Project not found for this user.")
    else:
        project = persistence.create_project(user_id=user_id, name=request.project_name)
        resolved_project_id = int(project["id"])

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
    user: dict | None = Depends(get_optional_user),
) -> GenerateResult:
    result = ppt_generator.generate(request)

    if not user:
        return result

    user_id = int(user["id"])
    resolved_project_id = request.project_id
    if resolved_project_id is not None:
        project = persistence.get_project(resolved_project_id)
        if not project or int(project["user_id"]) != user_id:
            raise HTTPException(status_code=403, detail="Project not found for this user.")
    else:
        project = persistence.create_project(user_id=user_id, name=request.deck_title)
        resolved_project_id = int(project["id"])

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
def download_artifact(artifact_name: str) -> FileResponse:
    safe_name = Path(artifact_name).name
    artifact_path = OUTPUT_DIR / safe_name

    if not artifact_path.exists() or not artifact_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found.")

    return FileResponse(
        path=artifact_path,
        filename=safe_name,
        media_type="application/octet-stream",
    )
