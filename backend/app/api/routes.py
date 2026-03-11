from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.app.models.schemas import (
    GeneratePptxRequest,
    GenerateResult,
    GenerateSowRequest,
    ParseResponse,
)
from backend.app.services.file_utils import OUTPUT_DIR
from backend.app.services.document_parser import DocumentParser
from backend.app.services.ppt_generator import PptGenerator
from backend.app.services.sow_generator import SowGenerator


router = APIRouter()

document_parser = DocumentParser()
sow_generator = SowGenerator()
ppt_generator = PptGenerator()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/v1/parse", response_model=ParseResponse)
async def parse_document(file: UploadFile = File(...)) -> ParseResponse:
    try:
        parsed_document = await document_parser.parse_upload(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ParseResponse(document=parsed_document)


@router.post("/api/v1/generate/sow", response_model=GenerateResult)
def generate_sow(request: GenerateSowRequest) -> GenerateResult:
    return sow_generator.generate(request)


@router.post("/api/v1/generate/pptx", response_model=GenerateResult)
def generate_pptx(request: GeneratePptxRequest) -> GenerateResult:
    return ppt_generator.generate(request)


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
