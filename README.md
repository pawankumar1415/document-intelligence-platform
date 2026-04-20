# BSBI Document Intelligence Platform

BSBI Document Intelligence turns uploaded source documents into branded consulting deliverables, and validates project narrative quality against configurable standards with AI-powered feedback and rewrite suggestions.

## What The Product Does

- Auth-first web app with React + Vite + TypeScript frontend and FastAPI backend
- Upload and parse `docx`, `txt`, and `pdf` source files
- Screen uploaded content against supported use cases before generation
- Chunk and index parsed content into PostgreSQL `pgvector`
- Generate branded deliverables using a selectable LLM provider and model
- Download generated `docx` and `pptx` artifacts
- Generate **Bid / Proposal Responses** from RFP or brief documents
- **Compare two document versions** side-by-side with AI-powered delta analysis
- **Extract structured registers** (risks, requirements, actions, stakeholders) via configurable schemas
- **Analytics dashboard** with validation trends, common issues, and recent activity
- **Clause Library** to save, search, and reuse reusable professional text blocks
- Chat with your project documents using RAG-backed conversational AI
- Validate single documents against configurable quality rubrics with AI scoring and rewrite
- Batch validate multiple documents from Excel/CSV upload or directly from SharePoint
- Admin panel for user management

## Product Flow

```mermaid
flowchart LR
    A[Login] --> B[Create or Reuse Project]
    B --> C[Upload docx/txt/pdf]
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
- `SQLite` for users, sessions, projects, documents, artifacts, chat history, rubrics, validation results
- `PostgreSQL + pgvector` for vector search
- Embeddings: local `sentence-transformers` or local `Ollama /api/embed`
- PDF extraction: `Docling` with OCR + table structure
- Switchable generation providers:
  - `OpenAI`
  - `Groq`
  - `Ollama`
  - `Azure OpenAI`

### Document Outputs
- `python-docx` for branded SOW generation
- `python-pptx` for branded presentation generation
- BSBI logo and presentation styling applied during export

## Features

### Studio
Upload documents, parse them, and generate branded SOW or PPTX deliverables. Supports `docx`, `pdf`, and `txt`. Generated artifacts are stored and downloadable.

### Chat
Conversational RAG interface. Ask questions about your project documents. Intent detection routes questions to either vector-search-backed answers or general LLM responses. Session history is preserved across the conversation.

### Validate Document
Single-document quality validation against a configurable rubric:
- **Layer 1** — Structure and quality check against named criteria (score 0–10). Thresholds: PASS ≥8, PASS WITH WARNINGS ≥6, FAIL <6.
- **Layer 2** — Internal consistency check for contradictions, date/figure conflicts.
- **AI Rewrite** — LLM-generated corrected version with word-level diff highlighting.
- Document can be typed manually, uploaded as a file, or pulled from SharePoint.
- Rubrics are user-owned and fully configurable (name, description, severity per criterion).

### Batch Validation
Validate many documents in one run:
- Upload an Excel (`.xlsx`) or CSV file, or browse and select a file from SharePoint.
- Excel auto-detection: recognises the NDA MPPR multi-row format (no header, each project spans 2–3 rows) and generic tabular header-based format.
- Results table shows per-document verdict, score, issues, and rewrite preview.
- Export all results to CSV.

### SharePoint Integration
Browse and select files directly from a Microsoft SharePoint site:
- Navigable folder tree with breadcrumb trail.
- File metadata (size, last modified, type icons).
- Used as an upload source in both Validate Document and Batch Validation.

### Bid / Proposal Response Generator
Generate a competitive proposal response document from any RFP, brief, or opportunity document:
- Parses the source document via the same pipeline as SOW and PPT.
- Generates 8 structured sections: Executive Overview, Understanding of Requirements, Proposed Approach, Solution Architecture, Delivery Plan, Team & Governance, Why Choose BSBI, Next Steps.
- Branded DOCX output with the same BSBI styling as SOW.
- Accepts optional "our key strengths" bullet points to personalise the response.

### Document Comparison
Compare two document versions side-by-side with AI analysis:
- Paste or upload two documents (Doc A = original, Doc B = revised).
- Returns an overall sentiment (improved / regressed / neutral), quality scores for both documents, a list of key improvements, a list of regressions, and a detailed change table by section.
- No document storage required — works on any two text bodies.

### Structured Data Extractor
Extract any type of structured entity from a document and download a formatted register:
- Five built-in schemas: Risks & Mitigations, Requirements, Action Items, Stakeholders, Decisions.
- Custom schemas: define your own entity label and fields.
- Results rendered as an in-page table and exported as a branded DOCX register.
- Custom schemas are user-owned and persist across sessions (built-in schemas cannot be deleted).

### Analytics Dashboard
Organisation-level visibility into document quality and activity:
- Overview stats: total documents parsed, artifacts generated, validations run, average compliance score, pass rate, saved clauses.
- Validation quality trend chart (bar chart, last 30 days, colour-coded by score band).
- Most common issues list aggregated across all validation results.
- Recent activity feed (documents, artifacts, validations, clauses).

### Clause Library
Save, search, and reuse professional text blocks:
- Auto-extract reusable clauses from any document using the LLM (identifies governance statements, scope paragraphs, methodology descriptions, etc.).
- Add clauses manually with a title, content, and comma-separated tags.
- Keyword search across all clauses.
- One-click copy to clipboard for insertion into new documents.

### Admin
User management panel (admin-only):
- View all registered users.
- Activate / deactivate accounts.
- Promote or demote admin status.
- Delete users.

## Technology Matrix

| Concern | Current Choice | Notes |
|---|---|---|
| Web UI | React + Vite + TypeScript | Separate dev server or backend-served build |
| API | FastAPI | Single backend for auth, parsing, retrieval, generation |
| App DB | SQLite | Local persistence for users/projects/artifacts/chat/rubrics |
| Vector DB | PostgreSQL + pgvector | Local Docker setup recommended on Windows |
| Embeddings | `huggingface_local` or `ollama` | Configurable via `EMBEDDING_BACKEND` |
| Hugging Face options | `nomic-ai/nomic-embed-text-v1.5`, `BAAI/bge-m3`, `intfloat/multilingual-e5-large-instruct` | Local sentence-transformers path |
| Ollama option | e.g. `qwen3-embedding:0.6b` | Uses local Ollama `/api/embed` |
| Generation Providers | OpenAI, Groq, Ollama, Azure OpenAI | Frontend-selectable |
| Azure Model Selection | Deployment names | Azure inference is deployment-based |
| SharePoint | Microsoft Graph API via `msal` | App-only client credentials flow |

## Embedding Options

The current backend is designed around open-source local embeddings. Supported embedding model IDs:

Hugging Face (`EMBEDDING_BACKEND=huggingface_local`):
- `nomic-ai/nomic-embed-text-v1.5` (default)
- `BAAI/bge-m3`
- `intfloat/multilingual-e5-large-instruct`

Ollama (`EMBEDDING_BACKEND=ollama`):
- Use any local embedding model exposed by Ollama, for example `qwen3-embedding:0.6b`

Default recommendation:
- Use `nomic-ai/nomic-embed-text-v1.5` for the first local deployment
- Move to `BAAI/bge-m3` if multilingual retrieval quality becomes the priority
- Use `qwen3-embedding:0.6b` on low-memory GPUs and move to `qwen3-embedding:4b` only if performance is acceptable

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

## SharePoint Setup

SharePoint access uses Microsoft Graph API with an app-only client credentials flow. No user sign-in is required at runtime.

### Prerequisites
- An Azure subscription with access to the tenant that owns your SharePoint site.
- Admin consent rights in that Azure AD tenant.

### Steps

1. **Switch to the correct Azure AD tenant** — the tenant must be the one that owns your SharePoint hostname (e.g. `yourcompany.sharepoint.com` lives in `yourcompany.onmicrosoft.com`).

2. **Create an App Registration** in that tenant:
   - Azure Portal → Azure Active Directory → App Registrations → New registration
   - Name: anything (e.g. `Doc Platform`)
   - Supported account types: Single tenant
   - Copy the **Application (client) ID** → `SHAREPOINT_CLIENT_ID`
   - Copy the **Directory (tenant) ID** → `SHAREPOINT_TENANT_ID`

3. **Create a client secret**:
   - App Registration → Certificates & Secrets → New client secret
   - Copy the **Value** (not the ID) → `SHAREPOINT_CLIENT_SECRET`

4. **Grant API permissions**:
   - App Registration → API Permissions → Add a permission → Microsoft Graph → Application permissions
   - Add `Sites.Read.All`
   - Add `Files.Read.All`
   - Click **Grant admin consent**

5. **Add to `.env`**:

```env
SHAREPOINT_TENANT_ID=<Directory (tenant) ID>
SHAREPOINT_CLIENT_ID=<Application (client) ID>
SHAREPOINT_CLIENT_SECRET=<Client secret value>
SHAREPOINT_SITE_URL=https://yourcompany.sharepoint.com/sites/yoursite
```

6. Install the required Python library:

```bash
pip install msal
```

The SharePoint picker in the UI will show a "not configured" state until all four values are set to real (non-placeholder) values.

### Troubleshooting: `Invalid hostname for this tenancy`

This error means the App Registration is in a different Azure AD tenant than the one that owns the SharePoint site. The app authenticates against the wrong tenant and Graph rejects the site lookup.

Fix: ensure `SHAREPOINT_TENANT_ID` is the Directory ID of the tenant that owns the SharePoint hostname, and that the App Registration was created in that same tenant. See the steps above.

## Configuration

Copy `.env.example` to `.env` and fill real secrets locally.

Core settings:

```env
DEFAULT_LLM_PROVIDER=openai
EMBEDDING_BACKEND=huggingface_local
EMBEDDING_MODEL_ID=nomic-ai/nomic-embed-text-v1.5
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=qwen3-embedding:0.6b
OLLAMA_EMBED_MODEL_ALLOWLIST=
DOCLING_OCR_ENGINE=rapidocr
DOCLING_FORCE_FULL_PAGE_OCR=false
PGVECTOR_DSN=postgresql://postgres:postgres@localhost:5432/document_intelligence
VECTOR_STORE_RESET_ON_MISMATCH=false
OPENAI_ENABLED=true
OPENAI_API_KEY=...
OPENAI_CHAT_MODEL=gpt-4o-mini
GROQ_ENABLED=true
GROQ_API_KEY=...
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
OLLAMA_ENABLED=true
OLLAMA_CHAT_MODEL=qwen3:0.6b
OLLAMA_DISABLE_THINK=true
OLLAMA_CHAT_NUM_PREDICT=280
OLLAMA_CHAT_NUM_CTX=3072
OLLAMA_CHAT_TIMEOUT_SECONDS=90
OLLAMA_KEEP_ALIVE=20m
AZURE_OPENAI_ENABLED=false
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_CHAT_DEPLOYMENTS_JSON=[{"id":"gpt-4o-mini","label":"GPT-4o Mini Deployment"}]

# SharePoint (optional — leave as placeholders to disable)
SHAREPOINT_TENANT_ID=YOUR_TENANT_ID_HERE
SHAREPOINT_CLIENT_ID=YOUR_CLIENT_ID_HERE
SHAREPOINT_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
SHAREPOINT_SITE_URL=https://yourtenant.sharepoint.com/sites/yoursite
```

Vector-store mismatch note:
- If you switch embedding model/backend and hit a startup error like `Configured embedding dimension does not match`, set:
  - `VECTOR_STORE_RESET_ON_MISMATCH=true`
- This auto-clears the local vector index (`document_chunks`) and re-initializes with the new embedding dimension.

Security note:
- `.env` is ignored by git
- If any real secret has already been stored in `.env`, rotate it before sharing the repo

## Python Dependencies

Install all Python dependencies:

```bash
pip install -r requirements.txt
```

For SharePoint support, also install:

```bash
pip install msal
```

For Excel batch validation support (already in requirements if pandas is listed):

```bash
pip install pandas openpyxl
```

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

Both routes are login-first. The first registered user automatically becomes an admin.

## End-To-End Local Test

1. Start Ollama and ensure your embedding model exists:

```bash
ollama serve
ollama pull qwen3-embedding:0.6b
```

2. Set embedding backend to Ollama in `.env`:

```env
EMBEDDING_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=qwen3-embedding:0.6b
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
- Upload a `.txt`, `.docx`, or `.pdf` file and parse
- Generate SOW
- Generate PPT
- Download artifacts
- Open Chat and ask a question about the document
- Open Validate Document, paste text, run validation
- Open Batch Validation, upload an Excel file, run batch

7. Optional backend test suite:

```bash
.\venv\Scripts\python.exe -m pytest -q backend\tests
```

## Recommended Local Ollama Models (Balanced For Local Machines)

LLM:
- `qwen3:0.6b`
- `llama3.2:1b`
- `gemma3:1b`

Embeddings:
- `qwen3-embedding:0.6b` (lighter local default)
- `nomic-embed-text`
- `mxbai-embed-large`

Suggested pull commands:

```bash
ollama pull qwen3:0.6b
ollama pull llama3.2:1b
ollama pull gemma3:1b
ollama pull qwen3-embedding:0.6b
ollama pull nomic-embed-text
ollama pull mxbai-embed-large
```

## Provider And Model Selection

- The frontend asks the backend for available provider/model choices through `GET /api/v1/providers/models`
- `OpenAI` and `Groq` models are fetched dynamically and filtered to usable chat models
- `Ollama` models are fetched from local `OLLAMA_BASE_URL/api/tags` and filtered to chat-capable models
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
- `POST /api/v1/generate/bid`

### Comparison
- `POST /api/v1/compare`

### Structured Extraction
- `GET /api/v1/extraction-schemas`
- `POST /api/v1/extraction-schemas`
- `GET /api/v1/extraction-schemas/{id}`
- `DELETE /api/v1/extraction-schemas/{id}`
- `POST /api/v1/extract`

### Analytics
- `GET /api/v1/analytics`

### Clause Library
- `GET /api/v1/clauses`
- `POST /api/v1/clauses`
- `DELETE /api/v1/clauses/{id}`
- `GET /api/v1/clauses/search`
- `POST /api/v1/clauses/auto-extract`

### Artifacts
- `GET /api/v1/artifacts`
- `GET /api/v1/artifacts/{artifact_name}`

### Chat
- `POST /api/v1/chat`

### Rubrics
- `GET /api/v1/rubrics`
- `POST /api/v1/rubrics`
- `GET /api/v1/rubrics/{id}`
- `DELETE /api/v1/rubrics/{id}`

### Validation
- `POST /api/v1/validate`
- `POST /api/v1/validate/batch`

### SharePoint
- `GET /api/v1/sharepoint/status`
- `GET /api/v1/sharepoint/sites`
- `GET /api/v1/sharepoint/libraries`
- `GET /api/v1/sharepoint/files`
- `POST /api/v1/sharepoint/download-and-parse`

### Admin
- `GET /api/v1/admin/users`
- `PATCH /api/v1/admin/users/{id}`
- `DELETE /api/v1/admin/users/{id}`

### Health
- `GET /health`

## Repository Layout

```text
backend/                 FastAPI app, parsing, retrieval, generation, persistence
  app/
    api/routes.py        All API endpoints
    models/schemas.py    Pydantic request/response models
    services/
      auth_service.py    Authentication, session tokens
      chat_service.py    RAG chat pipeline
      validation_service.py  Two-layer document validation
      sharepoint_service.py  Microsoft Graph API / SharePoint
      excel_parser.py    Excel/CSV batch parsing (MPPR + generic)
      llm_provider.py    Multi-provider LLM abstraction
      persistence.py     SQLite schema and CRUD
  rag_function_reference/  Reference implementation (NDA MPPR ingest/validate)
frontend/                React app
Documentation/           Plans, spec, work log
logo/                    Brand assets
```

## Current Scope

Included:
- Login/register (first user becomes admin)
- Project-scoped parsing (docx, pdf, txt)
- Local embeddings + pgvector retrieval
- Dynamic provider/model catalog
- Branded SOW, PPT, and Bid Response generation
- RAG chat with session memory
- Configurable rubric-based document validation (single + batch)
- SharePoint file browser integration
- Excel auto-detection (NDA MPPR multi-row format + generic tabular)
- Admin user management panel
- **Document Comparison** — side-by-side delta analysis of two document versions
- **Structured Data Extractor** — configurable schema-based entity extraction to DOCX register
- **Analytics Dashboard** — validation trends, common issues, recent activity
- **Clause Library** — save, search, and reuse professional text blocks with auto-extract

Not included yet:
- Background job queue for long-running batch jobs
- Enterprise SSO
- Collaborative editing
- Image ingestion

## Documentation

- [Product Plan](./Documentation/DOCUMENT_INTELLIGENCE_PLATFORM_PLAN.md)
- [Technical Spec](./Documentation/DEVELOPMENT_TECH_SPEC.md)
- [Work Log](./Documentation/WORK_LOG.md)