from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.app.api.routes import router
from backend.app.services.persistence import init_db


app = FastAPI(
    title="BSBI Document Intelligence Platform",
    version="0.1.0",
    description="Baby-step backend for document parsing and output generation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def initialize_app() -> None:
    init_db()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


if FRONTEND_DIST.exists():
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str) -> FileResponse:
        if (
            full_path == "health"
            or full_path.startswith("api/")
            or full_path.startswith("docs")
            or full_path.startswith("redoc")
            or full_path.startswith("openapi.json")
        ):
            raise HTTPException(status_code=404, detail="Not Found")

        requested_path = (FRONTEND_DIST / full_path).resolve()
        if requested_path.is_file() and requested_path.is_relative_to(FRONTEND_DIST):
            return FileResponse(requested_path)

        return FileResponse(FRONTEND_DIST / "index.html")
