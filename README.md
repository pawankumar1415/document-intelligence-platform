# BSBI Document Intelligence Platform

BSBI Document Intelligence turns uploaded source documents into branded consulting deliverables. The current slice supports document parsing, vector indexing, grounded retrieval, switchable LLM-backed generation, and export of BSBI-styled `SOW` and `PPTX` outputs.

## What The Product Does

- Auth-first web app with React + Vite + TypeScript frontend and FastAPI backend
- Upload and parse `docx` and `txt` source files
- Chunk and index parsed content into PostgreSQL `pgvector`
- Generate branded deliverables using a selectable LLM provider and model
- Download generated `docx` and `pptx` artifacts

## Product Flow

```mermaid
flowchart LR
    A[Login] --> B[Create or Reuse Project]
    B --> C[Upload docx/txt]
    C --> D[Parse Document]
    D --> E[Chunk Text]
    E --> F[Embeddings: Hugging Face or Ollama]
    F --> G[Postgres + pgvector Index]
    G --> H[Select Provider + Model]
    H --> I[Retrieve Relevant Chunks]
    I --> J[Generate SOW or PPT]
    J --> K[Apply BSBI Branding]
    K --> L[Download Artifact]
```

## Architecture

### Frontend
- `React`
- `Vite`
- `TypeScript`
- Login-first UI with protected routes
- Provider selector plus model selector driven by backend catalog

### Backend
- `FastAPI`
- `SQLite` for users, sessions, projects, documents, artifacts
- `PostgreSQL + pgvector` for vector search
- Embeddings: local `sentence-transformers` or local `Ollama /api/embed`
- Switchable generation providers:
  - `OpenAI`
  - `Groq`
  - `Azure OpenAI`

### Document Outputs
- `python-docx` for branded SOW generation
- `python-pptx` for branded presentation generation
- BSBI logo and presentation styling applied during export

## Technology Matrix

| Concern | Current Choice | Notes |
|---|---|---|
| Web UI | React + Vite + TypeScript | Separate dev server or backend-served build |
| API | FastAPI | Single backend for auth, parsing, retrieval, generation |
| App DB | SQLite | Local persistence for users/projects/artifacts |
| Vector DB | PostgreSQL + pgvector | Local Docker setup recommended on Windows |
| Embeddings | `huggingface_local` or `ollama` | Configurable via `EMBEDDING_BACKEND` |
| Hugging Face options | `nomic-ai/nomic-embed-text-v1.5`, `BAAI/bge-m3`, `intfloat/multilingual-e5-large-instruct` | Local sentence-transformers path |
| Ollama option | e.g. `qwen3-embedding:4b` | Uses local Ollama `/api/embed` |
| Generation Providers | OpenAI, Groq, Azure OpenAI | Frontend-selectable |
| Azure Model Selection | Deployment names | Azure inference is deployment-based |

## Embedding Options

The current backend is designed around open-source local embeddings. Supported embedding model IDs:

Hugging Face (`EMBEDDING_BACKEND=huggingface_local`):
- `nomic-ai/nomic-embed-text-v1.5` (default)
- `BAAI/bge-m3`
- `intfloat/multilingual-e5-large-instruct`

Ollama (`EMBEDDING_BACKEND=ollama`):
- Use any local embedding model exposed by Ollama, for example `qwen3-embedding:4b`

Default recommendation:
- Use `nomic-ai/nomic-embed-text-v1.5` for the first local deployment
- Move to `BAAI/bge-m3` if multilingual retrieval quality becomes the priority
- Use `qwen3-embedding:4b` if you prefer Ollama-managed local embeddings

Operational note:
- The first local embedding request downloads the Hugging Face model to the local cache, so initial startup or first parse can be noticeably slower

## Local pgvector Setup On Windows

The easiest local setup is Docker.

1. Install Docker Desktop
2. Start PostgreSQL with pgvector:

```bash
docker run --name bsbi-pgvector ^
  -e POSTGRES_PASSWORD=postgres ^
  -e POSTGRES_DB=document_intelligence ^
  -p 5432:5432 ^
  -d pgvector/pgvector:pg17
```

3. Enable the extension:

```bash
psql -h localhost -U postgres -d document_intelligence -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

4. Point the app to it:

```env
PGVECTOR_DSN=postgresql://postgres:postgres@localhost:5432/document_intelligence
```

## Configuration

Copy [.env.example](./.env.example) to `.env` and fill real secrets locally.

Core settings:

```env
DEFAULT_LLM_PROVIDER=openai
EMBEDDING_BACKEND=huggingface_local
EMBEDDING_MODEL_ID=nomic-ai/nomic-embed-text-v1.5
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=qwen3-embedding:4b
PGVECTOR_DSN=postgresql://postgres:postgres@localhost:5432/document_intelligence
OPENAI_ENABLED=true
OPENAI_API_KEY=...
OPENAI_CHAT_MODEL=gpt-4o-mini
GROQ_ENABLED=true
GROQ_API_KEY=...
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
AZURE_OPENAI_ENABLED=false
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_CHAT_DEPLOYMENTS_JSON=[{"id":"gpt-4o-mini","label":"GPT-4o Mini Deployment"}]
```

Security note:
- `.env` is ignored by git
- If any real secret has already been stored in `.env`, rotate it before sharing the repo

## Running The Project

### Split Dev Mode

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

### Single-Server Mode

```bash
cd frontend
npm run build
cd ..
uvicorn backend.app.main:app --reload
```

Open `http://localhost:8000`.

Both routes are login-first.

## End-To-End Local Test

1. Start Ollama and ensure your embedding model exists:

```bash
ollama serve
ollama pull qwen3-embedding:4b
```

2. Set embedding backend to Ollama in `.env`:

```env
EMBEDDING_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=qwen3-embedding:4b
```

3. Ensure PostgreSQL + pgvector is running and reachable from `PGVECTOR_DSN`.
4. Start backend:

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

5. Validate API health and embedding setup:
- `GET /health`
- `GET /api/v1/vector/status` (should show `embedding_backend: "ollama"`)

6. Start frontend (`npm run dev`) and run the functional flow:
- Login/register
- Upload a `.txt` or `.docx` file and parse
- Generate SOW
- Generate PPT
- Download artifacts

7. Optional backend test suite:

```bash
.\venv\Scripts\python.exe -m pytest -q backend\tests
```

## Provider And Model Selection

- The frontend asks the backend for available provider/model choices through `GET /api/v1/providers/models`
- `OpenAI` and `Groq` models are fetched dynamically and filtered to usable chat models
- `Azure OpenAI` exposes configured deployment names from env, not raw upstream model names
- Generated requests carry both `llm_provider` and `llm_model`

## API Surface

### Auth
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

### Project And Parsing
- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `POST /api/v1/parse`

### Generation And Model Discovery
- `GET /api/v1/providers/models`
- `GET /api/v1/vector/status`
- `POST /api/v1/embedding/config`
- `POST /api/v1/generate/sow`
- `POST /api/v1/generate/pptx`

### Artifacts
- `GET /api/v1/artifacts`
- `GET /api/v1/artifacts/{artifact_name}`

### Health
- `GET /health`

## Repository Layout

```text
backend/                 FastAPI app, parsing, retrieval, generation, persistence
frontend/                React app
Documentation/           Plans, spec, work log
logo/                    Brand assets
```

## Current Scope

Included now:
- Login/register
- Project-scoped parsing
- Local embeddings + pgvector retrieval
- Dynamic provider/model catalog
- Branded SOW and PPT generation

Not included yet:
- `pdf`, `xlsx`, or image OCR ingestion
- background job queue
- enterprise SSO
- collaborative editing

## Documentation

- [Product Plan](./Documentation/DOCUMENT_INTELLIGENCE_PLATFORM_PLAN.md)
- [Technical Spec](./Documentation/DEVELOPMENT_TECH_SPEC.md)
- [Work Log](./Documentation/WORK_LOG.md)
