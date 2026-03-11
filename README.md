# BSBI Document Intelligence Platform

BSBI Document Intelligence is a full-stack application that converts uploaded documents into business-ready outputs using retrieval + LLM generation.

Current outputs:
- Branded `SOW` (`.docx`)
- Branded `Presentation` (`.pptx`)

Supported source files in current slice:
- `.docx`
- `.txt`

## Core Capabilities

- Auth-first workflow (app always starts at login)
- Project-scoped document parsing and persistence
- PostgreSQL `pgvector` chunk indexing and similarity retrieval
- Switchable LLM provider per session:
  - `OpenAI`
  - `Groq`
  - `Azure OpenAI`
- Branded output generation (BSBI logo/styling applied in generated files)

## Architecture

- **Frontend**: React + Vite + TypeScript
- **Backend**: FastAPI (Python)
- **Relational persistence**: SQLite (`backend/data/app.db`) for users/projects/artifacts
- **Vector store**: PostgreSQL with `pgvector` extension
- **Generation pipeline**:
  1. Parse source document
  2. Chunk + embed + index vectors
  3. Retrieve relevant chunks
  4. Generate draft via selected LLM provider
  5. Render branded `.docx` / `.pptx`

## Repository Structure

```text
backend/                 FastAPI app and generation pipeline
frontend/                React UI
Documentation/           Plans, tech spec, and work log
logo/                    Brand assets
```

## Prerequisites

- Python `3.12+` (project currently tested in local `venv`)
- Node.js `20+` (you are on `25.8.0`, which is fine)
- PostgreSQL with `pgvector` enabled

## Configuration

Create and populate `.env` in project root (starter template is included):

- `PGVECTOR_DSN`
- `OPENAI_API_KEY`
- `GROQ_API_KEY`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- model/deployment names for each provider

Important: `.env` is git-ignored and should never be committed.

## Running the Project

### Option A: Split dev mode (recommended for UI development)

Terminal 1:

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Option B: Single-server mode (backend serves built frontend)

```bash
cd frontend
npm run build
cd ..
uvicorn backend.app.main:app --reload
```

Open `http://localhost:8000`.

## API Surface

Health:
- `GET /health`
- `GET /api/v1/vector/status`

Auth:
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

Projects (auth required):
- `POST /api/v1/projects`
- `GET /api/v1/projects`

Document and generation (auth required):
- `POST /api/v1/parse`
- `POST /api/v1/generate/sow`
- `POST /api/v1/generate/pptx`

Artifacts (auth required):
- `GET /api/v1/artifacts`
- `GET /api/v1/artifacts/{artifact_name}`

Generated files are stored in `backend/output/`.

## Notes

- Invalid or corrupted `.docx` files return `400` validation errors (not server crashes).
- If vector indexing is misconfigured (missing DSN/keys), parse returns a clear error from backend.
- Provider switching is controlled from frontend and passed to backend on parse/generate requests.

## Documentation

- [Product Plan](./Documentation/DOCUMENT_INTELLIGENCE_PLATFORM_PLAN.md)
- [Technical Spec](./Documentation/DEVELOPMENT_TECH_SPEC.md)
- [Work Log](./Documentation/WORK_LOG.md)
