from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import router
from backend.app.services.persistence import init_db
from backend.app.services.vector_store import init_vector_store, vector_store_status


app = FastAPI(
    title="AI Narrative Search",
    version="1.0.0",
    description="Score narrative text, highlight abnormalities, and process batches with AI.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174",
        "http://127.0.0.1:5174",
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
    import logging
    logger = logging.getLogger(__name__)
    init_db()
    if vector_store_status()["configured"]:
        try:
            init_vector_store()
        except Exception as exc:
            logger.warning(
                "pgvector unavailable — reference/abnormality features disabled. "
                "Create the database and restart to enable them. Error: %s", exc
            )


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