# Multi-Product Codebase Structure Guide

## Purpose

This guide defines the structure and development practices to follow when adding new products to this repository. The goal is to keep every product easy to understand, run, test, document, and maintain while allowing each product to remain independently deployable and evolvable.

Example:

```text
Document Intelligence Platform/
  backend/
  frontend/
  Documentation/
  README.md
  requirements.txt

  products/
    ai-narrative/
      backend/
      frontend/
      README.md
      requirements.txt
      pytest.ini
```

## Product Boundaries

Each product must have a clear ownership boundary. The root folder contains the primary Document Intelligence Platform. Additional products should live inside `products/<product-name>/` and should include their own backend, frontend, tests, README, configuration, and dependency files where needed.

Example:

```text
products/
  ai-narrative/
    backend/
    frontend/
    README.md
    requirements.txt
    pytest.ini

  contract-review/
    backend/
    frontend/
    README.md
    requirements.txt
    pytest.ini
```

## README First

Every product must include a `README.md` that explains what the product does, how it is structured, how to configure it, how to run it locally, how to test it, and what API surface it exposes. The README should be written for a developer joining the project later.

Example:

````markdown
# AI Narrative Search

AI Narrative Search scores narrative text against configurable rubrics, reference examples, and financial data.

## Running The Backend

```bash
cd products/ai-narrative
uvicorn backend.app.main:app --reload --port 8001
```

## Running The Frontend

```bash
cd products/ai-narrative/frontend
npm install
npm run dev
```
````

## Backend Structure

Backends should follow a modular FastAPI structure. Keep the application entrypoint, API routes, Pydantic schemas, and business logic separated. Routes should orchestrate requests and responses; services should own business behavior.

Example:

```text
backend/
  app/
    main.py
    config.py
    api/
      routes.py
    models/
      schemas.py
    services/
      auth_service.py
      persistence.py
      llm_provider.py
      provider_catalog.py
      vector_store.py
```

## Frontend Structure

Frontends should follow a React + Vite + TypeScript structure. Keep routes in `App.tsx`, shared application state in `context/`, API wrappers in `services/`, reusable UI pieces in `components/`, page-level screens in `views/` or `pages/`, and shared TypeScript contracts in `types/`.

Example:

```text
frontend/
  src/
    App.tsx
    main.tsx
    App.css
    index.css
    components/
      Sidebar.tsx
      ProtectedRoute.tsx
      ModelControlBar.tsx
    context/
      AppStateContext.tsx
    services/
      api.ts
    types/
      app.ts
    views/
      LoginView.tsx
      SettingsView.tsx
      AdminView.tsx
```

## Shared API Contracts

Backend Pydantic schemas and frontend TypeScript types should mirror each other closely. This keeps request and response shapes predictable and reduces integration bugs.

Example:

```python
# backend/app/models/schemas.py
class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in_seconds: int
    user: AuthUserProfile
```

```ts
// frontend/src/types/app.ts
export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in_seconds: number;
  user: AuthUser;
};
```

## Configuration

Each product should use environment variables for secrets, provider settings, database paths, model configuration, and external integrations. Commit `.env.example`, but never commit real `.env` secrets.

Example:

```text
.env.example
requirements.txt
README.md
```

```env
DEFAULT_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OPENAI_API_KEY=...
DATABASE_URL=postgresql://user:password@localhost:5432/product_db
```

## Virtual Environments

Use a Python virtual environment for each backend runtime. Do not commit the virtual environment directory. Document the setup commands in the product README.

Example:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

For the root product, an existing local `venv/` may be used during development, but it should remain ignored by Git.

## Dependency Files

Each Python backend should have a `requirements.txt`. Each frontend should have a `package.json` and lockfile. Product-level dependency files make each product easier to install, test, and deploy independently.

Example:

```text
products/ai-narrative/
  requirements.txt
  frontend/
    package.json
    package-lock.json
```

## Tests

Every product backend should include tests under `backend/tests/`. Tests should cover persistence, routes, parsing, service behavior, provider catalog behavior, and edge cases. Mock external LLMs, databases, and network calls where possible.

Example:

```text
backend/
  tests/
    conftest.py
    test_persistence.py
    test_routes.py
    test_provider_catalog.py
    test_excel_parser.py
    test_chat_service.py
```

```bash
pytest backend/tests
```

## Test Configuration

Each product should include a `pytest.ini` when test discovery or Python path setup needs to be explicit. This makes test execution consistent across local machines and CI.

Example:

```ini
[pytest]
testpaths = backend/tests
pythonpath = .
```

## Persistence Layer

Keep database access in a dedicated persistence service. Route handlers should not contain raw table-management logic. Service modules should call persistence functions for create, read, update, delete, and analytics operations.

Example:

```text
backend/app/services/persistence.py
```

```python
def create_project(user_id: int, name: str) -> dict[str, Any]:
    ...

def list_projects(user_id: int) -> list[dict[str, Any]]:
    ...
```

## Service Layer

Business logic belongs in services, not directly inside route handlers. Use services for LLM calls, document parsing, scoring, generation, extraction, validation, SharePoint access, vector storage, and analytics.

Example:

```text
backend/app/services/
  document_parser.py
  validation_service.py
  llm_provider.py
  embedding_service.py
  vector_store.py
  sharepoint_service.py
```

## Provider Abstraction

LLM providers should be accessed through a provider abstraction. This allows the product to support OpenAI, Groq, Azure OpenAI, Ollama, or future providers without rewriting feature code.

Example:

```python
result = generate_json_object(
    provider=request.llm_provider,
    model=request.llm_model,
    messages=messages,
)
```

## Model Catalog

Expose provider and model options through a backend catalog endpoint. The frontend should read available providers and models from the backend instead of hardcoding runtime availability.

Example:

```text
GET /api/v1/providers/models
```

```ts
const catalog = await getProviderCatalog({ token });
```

## Authentication Pattern

Products should use login-first protected routes. Authentication state should be stored in frontend app state and sent to protected backend endpoints using bearer tokens.

Example:

```tsx
<ProtectedRoute>
  <AppLayout />
</ProtectedRoute>
```

```http
Authorization: Bearer <token>
```

## Admin Pattern

Admin endpoints should be protected separately from normal authenticated endpoints. The first registered user may become an admin for local/internal deployments.

Example:

```text
GET /api/v1/admin/users
PATCH /api/v1/admin/users/{id}
DELETE /api/v1/admin/users/{id}
```

## File Upload Pattern

File upload endpoints should use multipart form data and validate supported file types. Parsing logic should live in a parser or extractor service, not in the route body.

Example:

```python
@router.post("/api/v1/parse")
async def parse_document(file: UploadFile = File(...)):
    parsed_document = await document_parser.parse_upload(file)
```

## Generated Artifacts

Generated files such as DOCX, PPTX, registers, or exports should be saved as artifacts and exposed through download endpoints. Artifact metadata should be persisted so users can find previous outputs.

Example:

```text
GET /api/v1/artifacts
GET /api/v1/artifacts/{artifact_name}
```

## Frontend API Client

All frontend API calls should be centralized in `frontend/src/services/api.ts`. Views should call typed API helper functions instead of building raw fetch requests everywhere.

Example:

```ts
export const generateSow = async (
  request: GenerateSowRequest,
  options: AuthOptions,
): Promise<GenerateResult> => {
  return requestJson(`${API_BASE_URL}/generate/sow`, {
    method: "POST",
    headers: authHeaders(options.token),
    body: JSON.stringify(request),
  });
};
```

## App State

Shared frontend state should live in `AppStateContext`. Use this for auth session, selected provider/model, currently parsed document, current project, output artifacts, and provider catalog state.

Example:

```text
frontend/src/context/AppStateContext.tsx
```

```ts
const { token, user, llmProvider, llmModel, setSession, clearSession } = useAppState();
```

## Routing

Each product frontend should define routes clearly in `App.tsx`. Public routes such as login or shared links should be separate from protected product routes.

Example:

```tsx
<Routes>
  <Route path="/login" element={<LoginView />} />
  <Route
    path="/*"
    element={
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    }
  />
</Routes>
```

## Documentation Folder

Use the root `Documentation/` folder for cross-product architecture, planning, technical specs, and work logs. Product-specific documentation should stay in the product folder README unless it applies to the whole repository.

Example:

```text
Documentation/
  DOCUMENT_INTELLIGENCE_PLATFORM_PLAN.md
  DEVELOPMENT_TECH_SPEC.md
  WORK_LOG.md
  PRODUCT_CODEBASE_STRUCTURE_GUIDE.md
```

## Work Log

When major implementation milestones are completed, record the date, summary, changed areas, and important notes in a work log. This helps future developers understand why the code evolved.

Example:

```markdown
## 2026-03-11 16:25:30 +05:30

### Summary

- Added artifact download support.
- Rebuilt frontend routes.
- Updated backend schema contracts.

### Key Files Updated

- backend/app/api/routes.py
- frontend/src/App.tsx
- README.md
```

## Generated And Local Files

Generated folders, virtual environments, caches, local databases, local output files, and secret-bearing files should be excluded from Git. Keep `.gitignore` updated whenever a product adds new generated paths.

Example:

```text
venv/
.venv/
__pycache__/
.pytest_cache/
node_modules/
.env
dist/
outputs/
```

## Naming Practices

Use clear product names and folder names. Product folders should use lowercase kebab-case. Python modules should use lowercase snake_case. React components should use PascalCase.

Example:

```text
products/ai-narrative/
backend/app/services/narrative_scorer.py
frontend/src/views/NarrativeView.tsx
```

## New Product Checklist

When adding a new product, create the complete structure before adding deep feature logic. This keeps the product maintainable from the beginning.

Example:

```text
products/new-product/
  README.md
  requirements.txt
  pytest.ini
  backend/
    app/
      main.py
      config.py
      api/routes.py
      models/schemas.py
      services/
    tests/
      conftest.py
      test_routes.py
  frontend/
    package.json
    index.html
    src/
      App.tsx
      main.tsx
      services/api.ts
      context/AppStateContext.tsx
      types/app.ts
      components/
      views/
```

## Maintenance Rule

Prefer consistency over novelty. A new product should feel familiar to any developer who has worked on the root platform or `products/ai-narrative`. Introduce new patterns only when they solve a real limitation and document the decision in the product README.

Example:

```markdown
## Architecture Decision

This product uses a background worker because file processing may take several minutes.
The API remains FastAPI, while long-running jobs are queued separately.
```

---

## Port Convention

Each product must use a distinct, predictable pair of ports for its backend and frontend. The root platform holds the base ports. Each new product increments by one. This prevents conflicts when running multiple products simultaneously in development.

Example:

```text
Root Platform        backend: 8000   frontend: 5173
products/ai-narrative  backend: 8001   frontend: 5174
products/contract-review backend: 8002 frontend: 5175
```

Configure the Vite dev server to use the assigned frontend port and proxy to the matching backend port:

```ts
// frontend/vite.config.ts
export default defineConfig({
  server: {
    port: 5174,
    proxy: {
      "/api": "http://localhost:8001",
    },
  },
});
```

---

## Dual Database Pattern

Every product uses two data stores for different purposes. SQLite holds all relational metadata: users, sessions, configuration, audit records, and any structured data that does not need vector similarity search. PostgreSQL with the pgvector extension holds only vector embeddings for semantic retrieval. Do not store relational records in pgvector and do not store embeddings in SQLite.

Example:

```text
SQLite (data/narrative.db)
  users, sessions, rubrics, score_results, user_settings, financial_records

PostgreSQL + pgvector
  reference_narratives  — embeddings of gold-standard reference documents
  scored_narratives     — archive embeddings of submitted documents
```

```python
# persistence.py — relational metadata
def save_score_result(user_id: int, unique_id: str, score: float) -> int: ...

# vector_store.py — embeddings only
def upsert_reference_narratives(file_id: int, records: list[dict], embeddings: list) -> None: ...
```

---

## Data Directory

Each backend stores its SQLite database under a `data/` subdirectory inside the product root. This directory is created automatically on first startup and must be excluded from Git. Never commit database files.

Example:

```text
products/ai-narrative/
  data/
    narrative.db        ← created automatically, gitignored
```

```python
# main.py — create data directory on startup
import os
os.makedirs("data", exist_ok=True)
```

```text
# .gitignore
data/*.db
data/
```

---

## Test Isolation Pattern

All backend tests must run against an isolated in-memory SQLite database. Use `conftest.py` to monkeypatch the database path before any test module imports the persistence layer. This ensures tests never touch the real database, run in any order, and leave no state behind.

Example:

```python
# backend/tests/conftest.py
import pytest

@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("backend.app.services.persistence.DB_PATH", db_file)
    from backend.app.services import persistence
    persistence.init_db()
    yield
```

Each test gets its own fresh database automatically. No teardown needed. LLM calls and external services should be mocked separately using `unittest.mock.patch`.

---

## Evaluation Tests

Separate evaluation tests from unit tests. Unit tests run on every `pytest` invocation and must be fast and fully mocked. Evaluation tests hit real LLMs, vector stores, or golden datasets and are expensive — they should only run explicitly. Mark evaluation tests with a custom pytest marker and exclude them from the default run.

Example:

```ini
# pytest.ini
[pytest]
testpaths = backend/tests
pythonpath = .
markers =
    eval: marks tests as evaluation tests (deselect with '-m "not eval"')
```

```python
# backend/tests/eval/test_rag_accuracy.py
@pytest.mark.eval
def test_rag_golden_set():
    ...
```

```bash
# Run only unit tests (default)
pytest

# Run evaluation tests explicitly
pytest -m eval
```

---

## Thinking Tag Stripping

When using chain-of-thought models (Qwen, DeepSeek, o1-style models) the raw LLM response may contain internal reasoning wrapped in `<think>…</think>` or `<thinking>…</thinking>` tags. These must be stripped before the response is parsed or returned to the caller. Apply stripping universally in the LLM provider abstraction so all callers are protected.

Example:

```python
# llm_provider.py
import re

def _strip_thinking_tags(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL)
    return text.strip()
```

Apply this in every code path that reads a raw LLM completion before any JSON parsing or downstream use.

---

## Batch Processing Pattern

When an operation must run on many rows from an uploaded file, implement a dedicated batch service. The route handler reads the file and delegates to the batch service. The batch service iterates rows, calls the row-level service function for each, accumulates results, and returns a structured summary. Row-level errors must not abort the entire batch — capture them per row and include them in the output.

Example:

```python
# batch_service.py
def run_batch_score(raw_bytes: bytes, filename: str, user_id: int) -> BatchScoreResponse:
    records = parse_file(raw_bytes, filename)
    results = []
    for record in records:
        try:
            result = narrative_scorer.run_score(record, user_id)
            results.append(result)
        except Exception as exc:
            results.append({"unique_id": record["unique_id"], "error": str(exc)})
    return BatchScoreResponse(results=results, total=len(results))
```

```python
# routes.py — batch route delegates entirely to the service
@router.post("/batch/score")
async def batch_score(file: UploadFile, ...):
    content = await file.read()
    return batch_service.run_batch_score(content, file.filename, user.id)
```

---

## SharePoint Integration Pattern

Products that need to read files from Microsoft SharePoint use an app-only client credentials flow — no user sign-in is required. The SharePoint service authenticates with Azure AD using tenant ID, client ID, and client secret, then calls the Microsoft Graph API to browse document libraries and download files. The frontend uses a shared `SharePointPicker` component to browse and select files before submitting them to a backend route.

Example:

```python
# services/sharepoint_service.py
def download_file(library_id: str, item_id: str) -> bytes:
    token = _get_app_token()   # client_credentials grant
    url = f"{GRAPH_BASE}/sites/{SITE_ID}/drives/{library_id}/items/{item_id}/content"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.content
```

```env
SHAREPOINT_TENANT_ID=...
SHAREPOINT_CLIENT_ID=...
SHAREPOINT_CLIENT_SECRET=...
SHAREPOINT_SITE_URL=https://tenant.sharepoint.com/sites/mysite
```

```tsx
// SharePointPicker.tsx — reusable file browser component
<SharePointPicker
  acceptExtensions={[".xlsx", ".csv", ".docx", ".pdf"]}
  onSelect={(item) => handleSharePointFile(item)}
/>
```

---

## Views and Pages Convention

All frontend page-level screens must be placed in `src/views/`. The folder `src/pages/` must not be used in new products. If you encounter a `pages/` folder in the root platform it is legacy and should not be replicated. New views follow PascalCase naming with the `View` suffix.

Example:

```text
frontend/src/views/
  NarrativeView.tsx      ✓ correct
  BatchView.tsx          ✓ correct
  SettingsView.tsx       ✓ correct
```

```text
frontend/src/pages/
  NarrativePage.tsx      ✗ do not use — legacy pattern in root platform only
```

---

## Landing Page

Products may include a standalone marketing or onboarding page at `landing/index.html`. This file must be plain HTML with no build step — it should open directly in a browser without running the dev server. It is optional and should only be added if the product has a distinct user-facing entry point separate from the application itself.

Example:

```text
products/ai-narrative/
  landing/
    index.html    ← standalone, no build needed, open directly in browser
```

```html
<!-- landing/index.html — no framework, no bundler, self-contained -->
<!DOCTYPE html>
<html lang="en">
  <head><title>AI Narrative Search</title></head>
  <body>
    <!-- marketing content, links to the app at localhost:5174 -->
  </body>
</html>
```

---

## Onboarding Component

Products that have a non-obvious first-run workflow should include an `OnboardingGuide` component. This component renders a step-by-step tour that is shown once to new users and dismissed permanently on completion. Store the dismissed state in `localStorage` so it does not reappear after page reload. Do not use a modal — render it inline so it does not block the UI.

Example:

```tsx
// components/OnboardingGuide.tsx
const STORAGE_KEY = "narrative_onboarding_done";

export default function OnboardingGuide() {
  const [visible, setVisible] = useState(() => !localStorage.getItem(STORAGE_KEY));

  const dismiss = () => {
    localStorage.setItem(STORAGE_KEY, "1");
    setVisible(false);
  };

  if (!visible) return null;
  return (
    <div className="onboarding-guide">
      <p>Step 1: Upload a reference file to enable abnormality detection.</p>
      <button onClick={dismiss}>Got it</button>
    </div>
  );
}
```

---

## CORS Configuration

Every backend must configure CORS explicitly for its assigned frontend port. Do not use wildcard origins (`*`) even in development — always list the specific localhost origins. When the frontend port changes, the CORS config must be updated to match.

Example:

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Session TTL Convention

All products use an 8-hour bearer token session lifetime. This is enforced in the auth service. Do not introduce shorter or longer TTLs in new products without a documented reason. Token expiry must be checked on every protected endpoint.

Example:

```python
# auth_service.py
SESSION_TTL_SECONDS = 8 * 60 * 60  # 8 hours — do not change without documented reason

def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    expires_at = datetime.utcnow() + timedelta(seconds=SESSION_TTL_SECONDS)
    persistence.save_session(user_id, token, expires_at)
    return token
```

---

## Audit Trail Pattern

Any product that runs AI-powered scoring or generation on user data should maintain an audit trail. Store one record per invocation with: timestamp, user ID, model provider, model name, a short hash of the prompt template, the output score or verdict, and any relevant metadata. Use a 30-day rolling window to keep the table bounded. This enables drift detection and retrospective debugging without unbounded storage growth.

Example:

```python
# persistence.py
def save_audit_entry(
    user_id: int,
    unique_id: str,
    provider: str,
    model_name: str,
    prompt_hash: str,   # first 12 chars of SHA-256 of the prompt template
    score: float,
    verdict: str,
) -> None: ...

def purge_old_audit_entries(days: int = 30) -> None:
    cutoff = datetime.utcnow() - timedelta(days=days)
    # delete entries older than cutoff
    ...
```

```python
# Compute prompt hash before each LLM call
import hashlib
prompt_hash = hashlib.sha256(prompt_template.encode()).hexdigest()[:12]
```

---

## Auto-Detection on Ingest

When a product ingests a corpus of data (reference narratives, documents, knowledge base entries), it should run automatic analysis on a sample to detect domain context. Store the detected profile and use it to personalise the product experience: tailored suggested questions, domain-specific prompts, and adapted UI labels. Detection must be non-blocking — log and continue if it fails.

Example:

```python
# reference_service.py
def ingest_reference_file(raw_bytes, filename, user_id):
    records = parse_file(raw_bytes, filename)
    # ... embed and store records ...

    # non-blocking domain detection on a sample
    try:
        sample = records[:10]
        profile = domain_detector.detect_domain(sample_records=sample)
        persistence.save_domain_profile(user_id, profile)
    except Exception as exc:
        logger.warning("Domain detection skipped: %s", exc)
```

```python
# domain_detector.py
def detect_domain(sample_records: list[dict]) -> dict:
    # LLM call returns: domain_name, period_format, status_codes, suggested_questions
    ...
```

---

## Scripts Directory

Utility scripts that are not part of the application runtime (data migrations, quality checks, one-off exports, seed scripts) must live in a `scripts/` directory at the product or repository root. Scripts must not be imported by application code. Each script should be runnable standalone from the command line.

Example:

```text
scripts/
  quality_check.py       ← standalone, run with: python scripts/quality_check.py
  seed_reference_data.py
  export_audit_log.py
```

```python
# scripts/quality_check.py
if __name__ == "__main__":
    # self-contained — no imports from backend.app
    ...
```

---

## Gitignore Per Product

The root `.gitignore` covers patterns that apply across the whole repository. When a product introduces paths that are not covered by the root ignore (product-specific databases, output directories, caches, local env files), add them to the root `.gitignore` with a comment identifying the product. Do not create separate per-product `.gitignore` files.

Example:

```text
# .gitignore (root)

# ai-narrative product
products/ai-narrative/data/
products/ai-narrative/backend/.env
products/ai-narrative/frontend/dist/
products/ai-narrative/.venv/

# contract-review product
products/contract-review/data/
products/contract-review/backend/.env
```
