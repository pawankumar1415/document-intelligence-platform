# AI Narrative Search

A standalone narrative quality scoring platform built for BSBI Consulting and Data Analytics.
Scores narrative text against customisable rubrics, detects semantic abnormalities against a
reference corpus, cross-references financial data for discrepancy checking, and generates
AI-powered rewrites — for single documents or thousands of rows in an Excel batch.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Prerequisites](#prerequisites)
3. [Environment Configuration](#environment-configuration)
4. [Database Setup](#database-setup)
5. [Docker Setup (pgvector)](#docker-setup-pgvector)
6. [Running the Backend](#running-the-backend)
7. [Running the Frontend](#running-the-frontend)
8. [Running the Tests](#running-the-tests)
9. [Landing Page](#landing-page)
10. [API Reference](#api-reference)
11. [File Format Requirements](#file-format-requirements)
12. [Scoring Engine](#scoring-engine)
13. [Reference Library](#reference-library)
14. [Standards — Rules & Financial Data](#standards--rules--financial-data)
15. [AI Performance Drift](#ai-performance-drift)
16. [LLM Providers](#llm-providers)
17. [SharePoint Integration](#sharepoint-integration)
18. [Project Structure](#project-structure)

---

## Architecture

```
products/ai-narrative/
├── backend/              # FastAPI application (port 8001)
│   ├── app/
│   │   ├── main.py       # FastAPI entrypoint, startup hooks
│   │   ├── config.py     # env() helper, path resolution, default_llm_provider()
│   │   ├── api/
│   │   │   └── routes.py # All REST endpoints under /api/v1/
│   │   ├── models/
│   │   │   └── schemas.py # Pydantic request/response models
│   │   └── services/
│   │       ├── persistence.py        # SQLite (10 tables) — users, rubrics, refs, scores, audit, financial, settings
│   │       ├── vector_store.py       # PostgreSQL + pgvector
│   │       ├── embedding_service.py  # HuggingFace local / Ollama
│   │       ├── llm_provider.py       # OpenAI / Groq / Azure / Ollama (thinking-tag stripping)
│   │       ├── provider_catalog.py   # Available models per provider
│   │       ├── excel_parser.py       # Multi-format parser: XLSX (A/B), CSV, DOCX tables, PDF tables
│   │       ├── text_extractor.py     # Plain-text extraction from DOCX, PDF (pdfplumber/pypdf), TXT
│   │       ├── narrative_scorer.py   # Three-layer scoring logic + audit logging
│   │       ├── rules_parser.py       # Parse compliance rules doc → rubric criteria
│   │       ├── financial_service.py  # Ingest financial data, Layer 3 record lookup
│   │       ├── drift_service.py      # Score audit aggregation, CSV export, trend detection
│   │       ├── batch_service.py      # Batch orchestration
│   │       ├── reference_service.py  # Reference ingest/delete
│   │       ├── chat_service.py       # RAG chat over reference library
│   │       ├── domain_detector.py    # Automatic domain detection on ingest
│   │       └── sharepoint_service.py # Microsoft Graph API — browse and download SharePoint files
│   └── tests/
│       ├── conftest.py
│       ├── test_persistence.py
│       ├── test_excel_parser.py
│       ├── test_narrative_scorer.py
│       ├── test_routes.py
│       ├── test_routes_extended.py
│       ├── test_standards.py         # Rules parser + financial service + drift service
│       ├── test_chat_service.py
│       ├── test_vector_store.py
│       ├── test_reference_service.py
│       ├── test_batch_service.py
│       ├── test_text_extractor.py
│       └── test_domain_detector.py
├── frontend/             # React 19 + Vite + TypeScript (port 5174)
│   └── src/
│       ├── views/        # NarrativeView, BatchView, ReferenceLibraryView, StandardsView, AnalyticsView, ...
│       ├── components/   # Sidebar, ModelControlBar, ProtectedRoute
│       ├── context/      # AppStateContext (token, provider, rubrics)
│       ├── services/     # api.ts — typed wrappers for all endpoints
│       ├── utils/        # diff.ts — word-level LCS diff for rewrite comparison
│       └── types/        # app.ts — TypeScript types
├── landing/
│   └── index.html        # Standalone marketing page (no build needed)
└── README.md
```

**Data stores:**
- **SQLite** — user accounts, sessions, rubrics, reference file metadata, score history, user settings, financial upload records, score audit trail
- **PostgreSQL + pgvector** — narrative embeddings for similarity retrieval

---

## Prerequisites

| Dependency | Minimum version | Purpose |
|---|---|---|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend dev server |
| PostgreSQL | 16+ | pgvector extension host (use `pgvector/pgvector:latest` Docker image) |
| pgvector extension | 0.7+ | Vector similarity search |
| Ollama | latest | Default LLM and embedding provider |

Pull the default Ollama models:

```bash
ollama pull qwen3.5:0.8b           # default LLM
ollama pull qwen3-embedding:0.6b   # default embedding model (1024-dim)
```

---

## Environment Configuration

Create `products/ai-narrative/.env` (the file is gitignored). Copy `.env.example` as a
starting point. The minimum required set is `PGVECTOR_DSN` and at least one LLM provider.

```env
# ── PostgreSQL + pgvector ──────────────────────────────────
PGVECTOR_DSN=postgresql://postgres:postgres@localhost:5432/document_intelligence
# Auto-reset pgvector tables when embedding dimension changes
VECTOR_STORE_RESET_ON_MISMATCH=false

# ── Default LLM selection ──────────────────────────────────
# Provider: openai | groq | azure_openai | ollama  (default: ollama)
DEFAULT_LLM_PROVIDER=ollama

# ── Ollama ────────────────────────────────────────────────
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=qwen3.5:0.8b
OLLAMA_CHAT_TIMEOUT_SECONDS=90

# ── Embedding Model ────────────────────────────────────────
# Backend: huggingface_local | ollama  (default: ollama)
EMBEDDING_BACKEND=ollama
# Model for ollama backend (dimension: qwen3-embedding:0.6b = 1024)
OLLAMA_EMBED_MODEL=qwen3-embedding:0.6b
# Model for huggingface_local backend
EMBEDDING_MODEL_ID=nomic-ai/nomic-embed-text-v1.5

# ── OpenAI ────────────────────────────────────────────────
OPENAI_ENABLED=true
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL=gpt-4o-mini

# ── Groq ──────────────────────────────────────────────────
GROQ_ENABLED=true
GROQ_API_KEY=gsk_...
GROQ_CHAT_MODEL=llama-3.3-70b-versatile

# ── Azure OpenAI ──────────────────────────────────────────
AZURE_OPENAI_ENABLED=false
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-10-21
```

---

## Database Setup

SQLite tables are created automatically on startup — no migration needed. The following
tables are managed automatically:

- `users`, `sessions` — authentication
- `rubrics`, `rubric_criteria` — scoring criteria
- `reference_files` — reference library metadata
- `score_results` — scoring history
- `user_settings` — per-user active rules rubric reference
- `financial_uploads`, `financial_records` — Standards financial data
- `score_audit` — per-score audit trail for drift analysis (30-day rolling)

For PostgreSQL, ensure the database exists and the `vector` extension is installed:

```bash
psql -U postgres -c "CREATE DATABASE document_intelligence;"
psql -U postgres -d document_intelligence -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

The `reference_narratives` and `scored_narratives` tables (with `VECTOR(1024)` columns and
IVFFlat indexes) are created automatically when the backend starts if `PGVECTOR_DSN` is set.

> **Embedding dimension mismatch**: if you change the embedding model at runtime via the
> Settings UI, the backend calls `init_vector_store()` immediately. With
> `VECTOR_STORE_RESET_ON_MISMATCH=true` any dimension mismatch causes an automatic table
> drop and recreation — all reference files must be re-uploaded after this.

---

## Docker Setup (pgvector)

The quickest way to get PostgreSQL with the pgvector extension running locally is via
Docker. The official `pgvector/pgvector` image ships with the extension pre-installed —
no separate `CREATE EXTENSION` step is needed, as the backend calls `init_vector_store()`
on startup which runs it automatically.

### Single container (quickstart)

```bash
docker run -d \
  --name bsbi-pgvector \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=document_intelligence \
  -p 5432:5432 \
  pgvector/pgvector:latest
```

Then set the connection string in your `.env`:

```env
PGVECTOR_DSN=postgresql://postgres:postgres@localhost:5432/document_intelligence
```

### Enable the pgvector extension

After the container is running, enable the vector extension in the target database:

```bash
docker exec -it bsbi-pgvector psql -U postgres -d document_intelligence -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

> The backend also calls `CREATE EXTENSION IF NOT EXISTS vector` automatically via
> `init_vector_store()` on startup — running the command above manually is useful to
> verify the extension is available before first launch.

### Docker Compose (pgvector only)

The backend runs locally via `uvicorn` — only pgvector needs Docker. Create a
`docker-compose.yml` in `products/ai-narrative/`:

```yaml
version: "3.9"

services:
  pgvector:
    image: pgvector/pgvector:latest
    container_name: bsbi-pgvector
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: document_intelligence
    ports:
      - "5432:5432"
    volumes:
      - pgvector_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  pgvector_data:
```

Start pgvector:

```bash
docker compose up -d
```

Then run the backend normally:

```bash
uvicorn backend.app.main:app --reload --port 8001
```

### Stopping and cleaning up

```bash
# Stop containers (data volume is preserved)
docker compose down

# Remove containers and all pgvector data
docker compose down -v
```

---

## Running the Backend

All commands are run from the **product root** (`products/ai-narrative/`):

```bash
cd products/ai-narrative

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn[standard] pydantic python-dotenv \
            openpyxl pandas psycopg2-binary pgvector \
            sentence-transformers passlib[pbkdf2] \
            openai groq httpx pdfplumber python-docx \
            pytest httpx

# Start the API server
uvicorn backend.app.main:app --reload --port 8001
```

The API is available at `http://localhost:8001`.
Interactive docs (Swagger UI) at `http://localhost:8001/docs`.

---

## Running the Frontend

```bash
cd products/ai-narrative/frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

Frontend runs at `http://localhost:5174`.
API calls are proxied to `http://localhost:8001` via the Vite config.

---

## Running the Tests

Tests use an isolated in-memory SQLite per test (monkeypatched path) and mock all LLM calls.
No live database or LLM key is required.

```bash
cd products/ai-narrative

# Run all tests
pytest

# Run a specific file
pytest backend/tests/test_standards.py -v

# Run with coverage
pytest --cov=backend.app --cov-report=term-missing
```

**Test files:**

| File | Coverage |
|---|---|
| `test_persistence.py` | User CRUD, sessions, rubrics, reference files, score results, analytics |
| `test_excel_parser.py` | Column detection (all formats), extra fields, error cases |
| `test_narrative_scorer.py` | Verdict logic, scoring prompts, Layer 1 + 2, persistence |
| `test_routes.py` | Auth endpoints, health, rubrics, score, analytics, admin |
| `test_routes_extended.py` | Chat, domain detection, batch, SharePoint, column detection |
| `test_standards.py` | Rules parser, financial service, drift service, Standards API routes |
| `test_chat_service.py` | RAG chat, source retrieval, context building |
| `test_vector_store.py` | pgvector init, dimension guard, upsert, query |
| `test_reference_service.py` | Reference ingest, delete, embedding pipeline |
| `test_batch_service.py` | Batch orchestration, row-level scoring, CSV export |
| `test_text_extractor.py` | DOCX / PDF / plain text extraction |
| `test_domain_detector.py` | Domain profile detection, status code parsing |

---

## Landing Page

The landing page is a standalone HTML file — no build step needed.

```bash
# Open directly in a browser
open products/ai-narrative/landing/index.html
# or
start products/ai-narrative/landing/index.html   # Windows
```

It references the logos from `../frontend/public/` relative to the landing directory.

---

## API Reference

All endpoints are prefixed with `/api/v1/`. All protected endpoints require:
`Authorization: Bearer <token>`

### Authentication

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Register new account |
| POST | `/auth/login` | — | Login, returns bearer token |

**Register / Login body:**
```json
{ "email": "user@example.com", "password": "secret123" }
```

**Auth response:**
```json
{ "access_token": "abc123...", "token_type": "bearer", "expires_in": 86400, "user": { "id": 1, "email": "...", "is_admin": true } }
```

---

### Rubrics

| Method | Path | Description |
|---|---|---|
| GET | `/rubrics` | List all rubrics (default rubric created on first call) |
| POST | `/rubrics` | Create a custom rubric |
| DELETE | `/rubrics/{id}` | Delete a rubric (cannot delete default) |

**Create rubric body:**
```json
{
  "name": "My Rubric",
  "description": "Optional description",
  "criteria": [
    { "name": "Clarity", "description": "Clear and readable prose", "severity": "high" }
  ]
}
```

---

### Scoring

| Method | Path | Description |
|---|---|---|
| POST | `/score` | Score a single narrative |
| POST | `/score/batch` | Score all rows in an uploaded Excel/CSV/DOCX/PDF |
| GET | `/scores` | List score history for the authenticated user |

**Single score body (JSON):**
```json
{
  "unique_id": "PROJ-001",
  "document_name": "Q1 Progress Report",
  "narrative": "The project has progressed well...",
  "rubric_id": null,
  "llm_provider": "ollama",
  "llm_model": "qwen3:4b",
  "top_k_references": 5
}
```

When `rubric_id` is `null`, the scorer checks for an active custom rules rubric (from Standards).
If none exists, the default rubric is used.

**Batch score — multipart form:**
```
file: <Excel, CSV, DOCX, or PDF>
rubric_id: 1           (optional)
llm_provider: ollama   (optional)
llm_model: qwen3:4b    (optional)
top_k_references: 5    (optional)
id_column: project_id  (optional — skip auto-detection)
narrative_column: text (optional — skip auto-detection)
```

**Score result shape:**
```json
{
  "overall_verdict": "PASS",
  "layer1": {
    "compliance_score": 8.5,
    "passed": ["Clarity", "Structure"],
    "issues": ["Completeness: missing milestone dates [MEDIUM]"]
  },
  "layer2": {
    "abnormalities": [],
    "reference_quality_score": 0.0,
    "patterns_followed": ["Good structure"],
    "references_used": 0
  },
  "layer3": null,
  "rewritten_narrative": "",
  "meta": {
    "unique_id": "PROJ-001",
    "document_name": "Q1 Progress Report",
    "rubric_id": 1,
    "rubric_name": "Default Narrative Rubric",
    "references_used": 0,
    "provider": "ollama",
    "model_name": "qwen3:4b",
    "has_custom_rules": false,
    "has_financial_data": false,
    "prompt_hash": "a3f1d8b29c4e"
  }
}
```

`layer3` is `null` when no financial data is uploaded. When present:
```json
{
  "discrepancies": [
    {
      "type": "cost_overrun",
      "description": "Narrative claims costs on target but data shows £1.2M overrun.",
      "severity": "high",
      "narrative_claim": "costs remain within budget",
      "data_value": "£12.4M actual vs £11.2M planned"
    }
  ],
  "financial_alignment_score": 6.5,
  "aligned_items": ["Schedule aligned with data"],
  "financial_record_found": true
}
```

---

### Reference Library

| Method | Path | Description |
|---|---|---|
| GET | `/references` | List indexed reference files |
| POST | `/references/ingest` | Upload and index a reference file |
| DELETE | `/references/{id}` | Delete file and remove its embeddings |
| GET | `/references/periods` | List detected reporting periods for chat filtering |

**Ingest — multipart form:**
```
file: <Excel or CSV>
description: "Q3 2024 approved reference narratives"  (optional)
```

---

### Standards

| Method | Path | Description |
|---|---|---|
| GET | `/standards/rules` | Get current rules + financial status (`StandardsStatus`) |
| POST | `/standards/rules/upload` | Upload rules document; LLM extracts criteria and creates a rubric |
| DELETE | `/standards/rules` | Remove custom rules; revert to default rubric |
| POST | `/standards/financial/upload` | Upload financial data file (Excel/CSV) |
| DELETE | `/standards/financial` | Remove financial data; deactivate Layer 3 |

**Upload rules — multipart form:**
```
file: <.docx, .pdf, .xlsx, .xls, or .csv>
```

**Rules upload response:**
```json
{
  "status": "ok",
  "rubric_id": 7,
  "criteria_count": 12,
  "filename": "compliance_standards_v3.docx",
  "message": "Extracted 12 criteria from compliance_standards_v3.docx"
}
```

**Upload financial data — multipart form:**
```
file: <.xlsx, .xls, or .csv>
```

The file must contain a column that matches the `unique_id` values used in narratives. The
system auto-detects the ID column by preferring columns named `id`, `uid`, `project_id`, etc.

**Financial upload response:**
```json
{
  "status": "ok",
  "filename": "financial_data_q1.xlsx",
  "record_count": 84,
  "message": "Indexed 84 financial records from financial_data_q1.xlsx"
}
```

**Standards status response:**
```json
{
  "rules": {
    "active": true,
    "rubric_id": 7,
    "rubric_name": "Compliance Standards v3",
    "criteria_count": 12,
    "source_filename": "compliance_standards_v3.docx"
  },
  "financial": {
    "active": true,
    "filename": "financial_data_q1.xlsx",
    "record_count": 84,
    "uploaded_at": "2026-04-29T09:15:00"
  }
}
```

---

### Analytics

| Method | Path | Description |
|---|---|---|
| GET | `/analytics` | Dashboard overview + recent 20 scores |
| GET | `/analytics/drift` | AI performance drift metrics (30-day) |
| GET | `/analytics/drift/export` | Download drift audit as CSV |

**Drift metrics response:**
```json
{
  "period_days": 30,
  "total_scored": 127,
  "avg_score": 7.84,
  "score_variance": 0.412,
  "trend_direction": "improving",
  "data_points": [...],
  "provider_changes": [...],
  "model_distribution": { "qwen3:4b": 102, "gpt-4o-mini": 25 },
  "custom_rules_usage_pct": 34.6,
  "financial_check_usage_pct": 18.1
}
```

---

### Provider Catalog

| Method | Path | Description |
|---|---|---|
| GET | `/providers/models` | Available LLM providers and models |
| GET | `/embedding/config` | Current embedding config + supported models |
| POST | `/embedding/config` | Update embedding backend/model (triggers vector store re-init) |

---

### Admin

All admin endpoints require `is_admin: true` on the authenticated user.

| Method | Path | Description |
|---|---|---|
| GET | `/admin/users` | List all user accounts |
| PATCH | `/admin/users/{id}` | Update `is_admin` or `is_active` |
| DELETE | `/admin/users/{id}` | Delete user and all their data |

The first registered user is automatically promoted to admin.

---

## File Format Requirements

The batch scorer and reference library accept `.xlsx`, `.xls`, `.csv`, `.docx`, and `.pdf`
files. Column detection is automatic — no fixed column order or naming is required.

### Supported formats

| Format | Detection | Description |
|---|---|---|
| **XLSX / XLS — Format A** | Structural (auto) | Multi-row project report: one project per block, narrative on a sub-row, RAG status in col 3 |
| **XLSX / XLS — Format B** | Header keywords | Generic tabular — first row is a header; ID and narrative columns detected by name |
| **CSV** | Header keywords | Same column detection as Format B |
| **DOCX** | First table | Reads the first table in the document; header row used for column detection |
| **PDF** | pdfplumber tables | Extracts tables from all pages; header row used for column detection |

> Plain-text extraction (for scoring a single document or rules parsing) uses
> `text_extractor.py` which handles `.docx` paragraphs, `.pdf` pages (pdfplumber with
> pypdf fallback), and `.txt` files.

### Column detection keywords

| Column type | Accepted header keywords |
|---|---|
| Unique ID | `id`, `uid`, `unique_id`, `ref`, `reference`, `project`, `code`, `identifier`, `name`, `document` |
| Narrative text | `narrative`, `text`, `description`, `content`, `body`, `summary`, `commentary`, `note`, `comment` |

**Rules:**
- Headers are matched case-insensitively
- Last word of a compound name is matched (e.g. `document_name` matches `name`)
- Rows with an empty ID are silently skipped
- All extra columns are preserved and included in the embedding content

**Example valid headers:**
```
project_id | narrative_text | site | date | value
ref        | description    | region
unique_id  | commentary
```

---

## Scoring Engine

### Layer 1 — Rubric Compliance

The LLM evaluates the narrative against each criterion in the active rubric and returns:
- A compliance score (0–10)
- A list of criteria the narrative passed
- A list of issues with severity tags `[HIGH]`, `[MEDIUM]`, or `[LOW]`

**Rubric resolution order:**
1. If `rubric_id` is supplied in the request, use it.
2. Else if the user has an active custom rules rubric (from Standards upload), use it.
3. Else use the user's default rubric.

**Verdicts:**
| Score | Verdict |
|---|---|
| ≥ 8.0 | PASS |
| ≥ 6.0 | PASS_WITH_WARNINGS |
| < 6.0 | FAIL |

### Layer 2 — Reference Abnormality Detection

If a reference corpus is indexed:
1. The narrative is embedded and the top-k most similar reference narratives are retrieved via cosine similarity (pgvector)
2. The LLM compares the submission against the retrieved examples
3. Abnormalities are returned as structured flags:

| Type | Description |
|---|---|
| `missing_information` | Content present in references but absent in the submission |
| `unusual_claim` | Statement that contradicts or is inconsistent with reference patterns |
| `data_discrepancy` | Numerical or factual values that deviate from expected ranges |
| `structural` | Organisation or flow that differs from reference standard |
| `tone` | Register, formality, or language style that deviates from corpus |

Layer 2 is skipped gracefully if no references are indexed.

### Layer 3 — Financial Accuracy Check

Activated only when financial data has been uploaded via **Standards → Financial Reference Data**.

1. The scorer looks up the `unique_id` in the financial records table (exact match, then case-insensitive fallback)
2. If a record is found, the LLM cross-references monetary and schedule claims in the narrative against the financial data values
3. Discrepancies are returned as structured flags:

| Type | Description |
|---|---|
| `cost_overrun` | Narrative claims costs on track but data shows overspend |
| `cost_underrun` | Narrative claims overspend but data shows underspend |
| `schedule_slip` | Narrative claim contradicts schedule data |
| `data_conflict` | Direct numerical conflict between narrative and data |
| `missing_reference` | Financial record exists but narrative makes no mention |

When `unique_id` has no matching financial record, `layer3` is returned as `null` (not an error).

### AI Rewrite

When a narrative scores below 8.0, the AI generates a rewritten version that:
- Preserves all original facts and figures
- Addresses the identified Layer 1 issues and Layer 2 abnormalities
- Matches the tone and structure of the reference corpus

### Prompt Hash Versioning

Every scoring run records a 12-character SHA-256 hash of the concatenated Layer 1 + Layer 2 +
Layer 3 system prompts. This hash is stored in the score audit trail and surfaced in the
`meta.prompt_hash` field of every result. When you change the prompts (e.g. after an update),
the hash changes and drift charts will show a clear before/after boundary.

---

## Reference Library

Upload reference Excel or CSV files containing your "gold standard" narratives.
These are embedded and stored in PostgreSQL + pgvector.

1. Navigate to **Reference Library** in the sidebar
2. Upload an `.xlsx`, `.xls`, or `.csv` file
3. The parser detects columns automatically and indexes all records
4. Embeddings are generated using the configured embedding model (default: `qwen3-embedding:0.6b` via Ollama)

**Changing the embedding model** (Settings → Embedding Model) triggers an immediate
vector store re-initialisation. With `VECTOR_STORE_RESET_ON_MISMATCH=true`, any dimension
mismatch causes an automatic table reset — all reference files must be re-uploaded.

### Automatic Domain Detection

When you upload a reference file, the system automatically analyses a sample of up to 10
narratives and detects your organisation's reporting domain:

- **Domain name** — e.g. "Nuclear Decommissioning Authority", "Government Digital Service"
- **Reporting period format** — e.g. `P-XX`, `Q1–Q4`, `Phase 1–5`
- **Status codes** — RAG labels and their meaning in your context
- **Key terminology** — abbreviations and acronyms specific to your domain
- **Suggested chat questions** — 5–8 questions tailored to your data

---

## Standards — Rules & Financial Data

The **Standards** page (`/standards`) provides two upload facilities that modify the
scoring engine's behaviour.

### Compliance Rules Document

Upload a document (`.docx`, `.pdf`, `.xlsx`, `.xls`, or `.csv`) that describes your
organisation's narrative standards. The system:

1. Extracts the text (python-docx for DOCX, pdfplumber for PDF, pandas for Excel/CSV)
2. Sends the content to the LLM which extracts structured criteria with name, description, and severity
3. Creates a new rubric and sets it as the user's active rules rubric

Once active, **all** scoring (single and batch) uses this rubric instead of the default.
The badge on the Standards page shows the extracted criteria count and source filename.

To revert to the default rubric, click **Remove rules**.

### Financial Reference Data

Upload an Excel or CSV file containing monetary and schedule data per project. The file
must have a column whose values match the `unique_id` values used in your narratives.
Once uploaded:

- Layer 3 activates automatically on every subsequent score run
- The scorer looks up each narrative's `unique_id` in the financial records table
- Discrepancies between the narrative text and the data values are surfaced as Layer 3 flags

To deactivate Layer 3, click **Remove financial data** on the Standards page.

---

## AI Performance Drift

The **Analytics → AI Performance Drift** tab tracks scoring behaviour over time to detect
model drift, prompt version changes, and provider switches.

### Score Audit Trail

Every scoring run appends a row to the `score_audit` SQLite table:

| Column | Description |
|---|---|
| `compliance_score` | Layer 1 score for this run |
| `verdict` | PASS / PASS_WITH_WARNINGS / FAIL / ERROR |
| `provider` | LLM provider name |
| `model_name` | Model ID |
| `prompt_hash` | First 12 chars of SHA-256 of concatenated system prompts |
| `has_custom_rules` | Whether a custom rules rubric was active |
| `has_financial_data` | Whether Layer 3 ran |
| `scored_at` | UTC timestamp |

Audit records older than 30 days are purged automatically.

### Drift Metrics

`GET /analytics/drift` returns:

| Field | Description |
|---|---|
| `data_points` | Daily averages: avg_score, pass/warn/fail counts, primary provider |
| `provider_changes` | Days where the primary provider changed between consecutive days |
| `score_variance` | Standard deviation of all daily avg_scores |
| `trend_direction` | `improving` / `declining` / `stable` based on linear regression slope |
| `model_distribution` | Count of runs per model ID |
| `custom_rules_usage_pct` | % of runs that used custom rules |
| `financial_check_usage_pct` | % of runs where Layer 3 was active |

### CSV Backup

`GET /analytics/drift/export` returns a CSV file with every audit record in the 30-day
window, suitable for archiving, auditing, or importing into Excel/BI tools.

---

## LLM Providers

Switch providers and models live from the **Model Control Bar** in the UI or from **Settings**.

| Provider | Env var | Notes |
|---|---|---|
| Ollama (default) | `OLLAMA_BASE_URL` | Fully offline — any locally pulled model |
| OpenAI | `OPENAI_API_KEY` | GPT-4o, GPT-4o Mini, GPT-4 Turbo |
| Groq | `GROQ_API_KEY` | Llama 3.1 70B, Mixtral 8×7B |
| Azure OpenAI | `AZURE_OPENAI_*` | Requires deployment name |

All providers strip `<think>…</think>` and `<thinking>…</thinking>` blocks from responses
before parsing, so models like DeepSeek-R1 and Qwen3 that emit chain-of-thought tokens
work correctly.

---

## SharePoint Integration

The backend can browse and download files directly from a SharePoint document library
using the Microsoft Graph API (`sharepoint_service.py`). Authentication uses the OAuth2
**Client Credentials** (app-only) flow — no user sign-in is required.

### Required Azure App Registration permissions

Your App Registration must have these **Application** permissions granted and
admin-consented under Microsoft Graph:

| Permission | Purpose |
|---|---|
| `Sites.Read.All` | Resolve the SharePoint site ID and list accessible sites |
| `Files.Read.All` | List document libraries, folders, and download files |

### Environment variables

Add these to your `.env`:

```env
SHAREPOINT_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
SHAREPOINT_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
SHAREPOINT_CLIENT_SECRET=your-client-secret-value
SHAREPOINT_SITE_URL=https://yourtenant.sharepoint.com/sites/yoursite
```

**Where to find each value:**

1. **`SHAREPOINT_TENANT_ID`** — Azure Portal → Azure Active Directory → Overview → Tenant ID
2. **`SHAREPOINT_CLIENT_ID`** — Azure Portal → Azure AD → App Registrations → your app → Application (client) ID
3. **`SHAREPOINT_CLIENT_SECRET`** — App Registration → Certificates & Secrets → New client secret → copy the **Value**
4. **`SHAREPOINT_SITE_URL`** — Copy your SharePoint site URL up to and including the site name (e.g. `https://yourtenant.sharepoint.com/sites/yoursite`)

> **Tenant ID mismatch:** If site resolution fails with a 400 error, your
> `SHAREPOINT_TENANT_ID` may not match the tenant that owns the SharePoint hostname.
> Fetch your real tenant ID from:
> `https://login.microsoftonline.com/<yourtenant>.onmicrosoft.com/.well-known/openid-configuration`
> and copy the GUID from the `token_endpoint` field.

### API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/sharepoint/sites` | List SharePoint sites accessible to the app |
| GET | `/sharepoint/libraries` | List document libraries in the configured site |
| GET | `/sharepoint/files` | List files and folders in a library |
| POST | `/extract/sharepoint` | Download a file and extract its text content |

SharePoint integration is optional — all other features work without it. When the four
credentials are not set, SharePoint endpoints return a descriptive configuration error
rather than failing silently. The **SharePoint Picker** component in the UI
(`SharePointPicker.tsx`) provides an in-app file browser backed by these endpoints.

---

## Project Structure

```
products/ai-narrative/
├── backend/
│   ├── .env                      # ← create this (gitignored)
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/routes.py
│   │   ├── models/schemas.py
│   │   └── services/
│   │       ├── auth_service.py
│   │       ├── batch_service.py
│   │       ├── chat_service.py
│   │       ├── domain_detector.py
│   │       ├── drift_service.py          # NEW — audit aggregation + trend
│   │       ├── embedding_service.py
│   │       ├── excel_parser.py
│   │       ├── financial_service.py      # NEW — financial data ingest + Layer 3 lookup
│   │       ├── llm_provider.py
│   │       ├── narrative_scorer.py
│   │       ├── persistence.py
│   │       ├── provider_catalog.py
│   │       ├── reference_service.py
│   │       ├── rules_parser.py           # NEW — rules document → rubric criteria
│   │       ├── sharepoint_service.py     # Microsoft Graph API — browse and download SharePoint files
│   │       ├── text_extractor.py         # Plain-text extraction from DOCX, PDF, TXT
│   │       └── vector_store.py
│   └── tests/
│       ├── conftest.py
│       ├── test_batch_service.py
│       ├── test_chat_service.py
│       ├── test_domain_detector.py
│       ├── test_excel_parser.py
│       ├── test_narrative_scorer.py
│       ├── test_persistence.py
│       ├── test_real_files.py
│       ├── test_reference_service.py
│       ├── test_routes.py
│       ├── test_routes_extended.py
│       ├── test_standards.py             # NEW — Standards + Drift tests
│       ├── test_text_extractor.py
│       └── test_vector_store.py
├── frontend/
│   ├── public/
│   │   ├── logo-bsbi.jpeg
│   │   └── logo-data.jpeg
│   ├── src/
│   │   ├── App.tsx
│   │   ├── App.css
│   │   ├── index.css
│   │   ├── components/
│   │   │   ├── ModelControlBar.tsx
│   │   │   ├── OnboardingGuide.tsx
│   │   │   ├── ProtectedRoute.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── context/
│   │   │   └── AppStateContext.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── utils/
│   │   │   └── diff.ts               # Word-level LCS diff for rewrite comparison
│   │   ├── types/
│   │   │   └── app.ts
│   │   └── views/
│   │       ├── AdminView.tsx
│   │       ├── AnalyticsView.tsx         # Overview + AI Performance Drift tabs
│   │       ├── BatchView.tsx
│   │       ├── ChatView.tsx
│   │       ├── DocsView.tsx
│   │       ├── LoginView.tsx
│   │       ├── NarrativeView.tsx
│   │       ├── ReferenceLibraryView.tsx
│   │       ├── SettingsView.tsx
│   │       └── StandardsView.tsx         # NEW — Rules + Financial upload panels
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── landing/
│   └── index.html
└── README.md
```