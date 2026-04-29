# AI Narrative Search

A standalone narrative quality scoring platform built for BSBI Consulting and Data Analytics.
Scores narrative text against customisable rubrics, detects semantic abnormalities against a
reference corpus, and generates AI-powered rewrites — for single documents or thousands of
rows in an Excel batch.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Prerequisites](#prerequisites)
3. [Environment Configuration](#environment-configuration)
4. [Database Setup](#database-setup)
5. [Running the Backend](#running-the-backend)
6. [Running the Frontend](#running-the-frontend)
7. [Running the Tests](#running-the-tests)
8. [Landing Page](#landing-page)
9. [API Reference](#api-reference)
10. [Excel Format Requirements](#excel-format-requirements)
11. [Scoring Engine](#scoring-engine)
12. [Reference Library](#reference-library)
13. [LLM Providers](#llm-providers)
14. [Project Structure](#project-structure)

---

## Architecture

```
products/ai-narrative/
├── backend/              # FastAPI application (port 8001)
│   ├── app/
│   │   ├── main.py       # FastAPI entrypoint, startup hooks
│   │   ├── config.py     # env() helper, path resolution
│   │   ├── api/
│   │   │   └── routes.py # All REST endpoints under /api/v1/
│   │   ├── models/
│   │   │   └── schemas.py # Pydantic request/response models
│   │   └── services/
│   │       ├── persistence.py        # SQLite (6 tables)
│   │       ├── vector_store.py       # PostgreSQL + pgvector
│   │       ├── embedding_service.py  # HuggingFace local / Ollama
│   │       ├── llm_provider.py       # OpenAI / Groq / Azure / Ollama
│   │       ├── provider_catalog.py   # Available models per provider
│   │       ├── excel_parser.py       # .xlsx / .xls / .csv parsing
│   │       ├── narrative_scorer.py   # Two-layer scoring logic
│   │       ├── batch_service.py      # Batch orchestration
│   │       └── reference_service.py  # Reference ingest/delete
│   └── tests/
│       ├── conftest.py
│       ├── test_persistence.py
│       ├── test_excel_parser.py
│       ├── test_narrative_scorer.py
│       └── test_routes.py
├── frontend/             # React 19 + Vite + TypeScript (port 5174)
│   └── src/
│       ├── views/        # NarrativeView, BatchView, ReferenceLibraryView, ...
│       ├── components/   # Sidebar, ModelControlBar, ProtectedRoute
│       ├── context/      # AppStateContext (token, provider, rubrics)
│       ├── services/     # api.ts — typed wrappers for all endpoints
│       └── types/        # app.ts — TypeScript types
├── landing/
│   └── index.html        # Standalone marketing page (no build needed)
└── README.md
```

**Data stores:**
- **SQLite** — user accounts, sessions, rubrics, reference file metadata, score history
- **PostgreSQL + pgvector** — narrative embeddings for similarity retrieval

---

## Prerequisites

| Dependency | Minimum version | Purpose |
|---|---|---|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend dev server |
| PostgreSQL | 14+ | pgvector extension host |
| pgvector extension | 0.5+ | Vector similarity search |

Install the pgvector extension once into your database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Environment Configuration

Create `products/ai-narrative/backend/.env` (the file is gitignored).
All variables have safe defaults where marked — minimum required set is the database URL
and at least one LLM key.

```env
# ── Database ──────────────────────────────────────────────
# SQLite path (default: products/ai-narrative/data/narrative.db)
DB_PATH=data/narrative.db

# PostgreSQL connection string — required for reference/abnormality features
DATABASE_URL=postgresql://user:password@localhost:5432/ai_narrative

# ── LLM Providers (add the ones you use) ──────────────────
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...

# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01

# Ollama base URL (default: http://localhost:11434)
OLLAMA_BASE_URL=http://localhost:11434

# ── Default LLM selection ──────────────────────────────────
# Provider: openai | groq | azure | ollama  (default: openai)
LLM_PROVIDER=openai
# Model name for the selected provider (default: gpt-4o-mini)
LLM_MODEL=gpt-4o-mini

# ── Embedding Model ────────────────────────────────────────
# Backend: huggingface_local | ollama  (default: huggingface_local)
EMBEDDING_BACKEND=huggingface_local
# HuggingFace model ID (default: nomic-ai/nomic-embed-text-v1.5)
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5
# Embedding dimension — must match the model (default: 768)
EMBEDDING_DIM=768
```

---

## Database Setup

SQLite tables are created automatically on startup — no migration needed.

For PostgreSQL, ensure the database exists and the `vector` extension is installed:

```bash
psql -U postgres -c "CREATE DATABASE ai_narrative;"
psql -U postgres -d ai_narrative -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

The `reference_narratives` table (with a `VECTOR(768)` column and IVFFlat index) is
created automatically when the backend starts if `DATABASE_URL` is set.

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
            openai groq httpx pytest httpx

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
pytest backend/tests/test_persistence.py -v

# Run with coverage
pytest --cov=backend.app --cov-report=term-missing
```

**Test files:**

| File | Coverage |
|---|---|
| `test_persistence.py` | User CRUD, sessions, rubrics, reference files, score results, analytics |
| `test_excel_parser.py` | Column detection (all formats), extra fields, error cases |
| `test_narrative_scorer.py` | Verdict logic, scoring prompts, layer 1 + 2, persistence |
| `test_routes.py` | Auth endpoints, health, rubrics, score, analytics, admin |

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

All endpoints are prefixed with `/api/v1/`.

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
{ "token": "abc123...", "user": { "id": 1, "email": "...", "is_admin": true } }
```

All protected endpoints require: `Authorization: Bearer <token>`

---

### Rubrics

| Method | Path | Description |
|---|---|---|
| GET | `/rubrics` | List all rubrics (default rubric is created on first call) |
| POST | `/rubrics` | Create a custom rubric |
| DELETE | `/rubrics/{id}` | Delete a rubric (cannot delete default) |

**Create rubric body:**
```json
{
  "name": "My Rubric",
  "description": "Optional description",
  "criteria": [
    { "name": "Clarity", "description": "Clear and readable prose", "weight": 1.0 }
  ],
  "is_default": false
}
```

---

### Scoring

| Method | Path | Description |
|---|---|---|
| POST | `/score` | Score a single narrative |
| POST | `/score/batch` | Score all rows in an uploaded Excel/CSV |
| GET | `/scores` | List score history for the authenticated user |

**Single score body (JSON):**
```json
{
  "unique_id": "PROJ-001",
  "document_name": "Q1 Progress Report",
  "narrative_text": "The project has progressed well...",
  "rubric_id": 1,
  "llm_provider": "openai",
  "llm_model": "gpt-4o-mini",
  "top_k_references": 5
}
```

**Batch score — multipart form:**
```
file: <Excel or CSV file>
rubric_id: 1          (optional)
llm_provider: openai  (optional)
llm_model: gpt-4o-mini (optional)
top_k_references: 5   (optional)
```

**Score result shape:**
```json
{
  "meta": { "unique_id": "PROJ-001", "document_name": "Q1 Progress Report" },
  "overall_verdict": "PASS",
  "layer1": {
    "compliance_score": 8.5,
    "passed": ["Clarity", "Structure"],
    "issues": ["Completeness: missing milestone dates [MEDIUM]"]
  },
  "layer2": {
    "abnormalities": [
      {
        "type": "missing_information",
        "description": "No budget variance mentioned",
        "severity": "LOW",
        "evidence": "Reference narratives consistently include spend-to-date figures"
      }
    ]
  },
  "rewritten_narrative": "The project has progressed well. As of Q1 end..."
}
```

---

### Reference Library

| Method | Path | Description |
|---|---|---|
| GET | `/references` | List indexed reference files |
| POST | `/references/ingest` | Upload and index a reference file |
| DELETE | `/references/{id}` | Delete file and remove its embeddings |

**Ingest — multipart form:**
```
file: <Excel or CSV>
description: "Q3 2024 approved reference narratives"  (optional)
```

**Response:**
```json
{ "message": "Indexed 142 records", "record_count": 142, "file_id": 3 }
```

---

### Analytics

| Method | Path | Description |
|---|---|---|
| GET | `/analytics` | Dashboard overview + recent 20 scores |

---

### Provider Catalog

| Method | Path | Description |
|---|---|---|
| GET | `/providers` | Available LLM providers and models |
| GET | `/embedding/catalog` | Current embedding config + supported models |
| POST | `/embedding/config` | Update embedding backend/model |

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

## Excel Format Requirements

The parser accepts `.xlsx`, `.xls`, and `.csv` files. Column detection is automatic —
no fixed column order or naming is required.

**Required columns (detected by keyword matching):**

| Column type | Accepted header keywords |
|---|---|
| Unique ID | `id`, `uid`, `ref`, `project`, `code`, `number`, `no` |
| Narrative text | `narrative`, `text`, `description`, `content`, `body`, `summary`, `commentary`, `note` |

**Rules:**
- Headers are matched case-insensitively
- Rows with an empty ID are silently skipped
- All extra columns are preserved and included in the embedding content
- Multi-row project report format is detected automatically by data structure (rows where col0 is empty, col1 is a project name, col3 is a RAG value)

**Example valid headers:**
```
project_id | narrative_text | site | date | value
ref        | description    | region
unique_id  | commentary
```

---

## Scoring Engine

### Layer 1 — Rubric Compliance

The LLM evaluates the narrative against each criterion in the selected rubric and returns:
- A compliance score (0–10)
- A list of criteria the narrative passed
- A list of issues with severity tags `[HIGH]`, `[MEDIUM]`, or `[LOW]`

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

Layer 2 is skipped gracefully if no references are indexed — a single soft warning is included instead of abnormality flags.

### AI Rewrite

When a narrative scores below 8.0, the AI generates a rewritten version that:
- Preserves all original facts and figures
- Addresses the identified Layer 1 issues and Layer 2 abnormalities
- Matches the tone and structure of the reference corpus

---

## Reference Library

Upload reference Excel or CSV files containing your "gold standard" narratives.
These are embedded and stored in PostgreSQL + pgvector.

1. Navigate to **Reference Library** in the sidebar
2. Upload an `.xlsx`, `.xls`, or `.csv` file
3. The parser detects columns automatically and indexes all records
4. Embeddings are generated using the configured embedding model (default: `nomic-ai/nomic-embed-text-v1.5`)

**Changing the embedding model** (Settings → Embedding Model) requires re-ingesting all
reference files — the old embeddings at a different dimension are incompatible.

### Automatic Domain Detection

When you upload a reference file, the system automatically analyses a sample of up to 10
narratives and detects your organisation's reporting domain and conventions:

- **Domain name** — identified from vocabulary and structure (e.g. "Nuclear Decommissioning Authority", "Government Digital Service")
- **Reporting period format** — e.g. `P-XX`, `Q1–Q4`, `Phase 1–5`
- **Status codes** — RAG labels and what they mean in your context
- **Key terminology** — abbreviations and acronyms specific to your domain
- **Suggested chat questions** — 5–8 questions tailored to your data that appear in the Knowledge Base Chat sidebar

The detected profile is stored per-user and used to build a domain-aware system prompt when
you chat, so the AI understands your terminology without any manual configuration.

**API endpoints:**
- `GET /api/v1/domain/profile` — retrieve the current detected profile
- `DELETE /api/v1/domain/profile` — clear and re-detect on next upload

---

## LLM Providers

Switch providers and models live from the **Model Control Bar** in the UI or from **Settings**.

| Provider | Env var | Notes |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | GPT-4o, GPT-4o Mini, GPT-4 Turbo |
| Groq | `GROQ_API_KEY` | Llama 3.1 70B, Mixtral 8×7B |
| Azure OpenAI | `AZURE_OPENAI_*` | Requires deployment name |
| Ollama | `OLLAMA_BASE_URL` | Fully offline — any locally pulled model |

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
│   │       ├── chat_service.py           # RAG chat over reference library
│   │       ├── domain_detector.py        # Automatic domain detection on ingest
│   │       ├── embedding_service.py
│   │       ├── excel_parser.py
│   │       ├── llm_provider.py
│   │       ├── narrative_scorer.py
│   │       ├── persistence.py
│   │       ├── provider_catalog.py
│   │       ├── reference_service.py
│   │       └── vector_store.py
│   └── tests/
│       ├── conftest.py
│       ├── test_excel_parser.py
│       ├── test_narrative_scorer.py
│       ├── test_persistence.py
│       └── test_routes.py
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
│   │   │   ├── ProtectedRoute.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── context/
│   │   │   └── AppStateContext.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── app.ts
│   │   └── views/
│   │       ├── AdminView.tsx
│   │       ├── AnalyticsView.tsx
│   │       ├── BatchView.tsx
│   │       ├── LoginView.tsx
│   │       ├── NarrativeView.tsx
│   │       ├── ReferenceLibraryView.tsx
│   │       └── SettingsView.tsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── landing/
│   └── index.html
└── README.md
```