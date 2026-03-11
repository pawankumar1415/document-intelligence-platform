# BSBI Document Intelligence Platform

Thin-slice implementation for:

- `.docx` / `.txt` parsing
- SOW draft generation (`.docx`)
- PPT draft generation (`.pptx`)
- BSBI-branded frontend flow (`dashboard -> upload -> generate -> outputs`)

## Backend Run

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

## Frontend Run

```bash
cd frontend
npm install
npm run dev
```

Optional API base URL:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

By default, frontend now calls relative `/api/*` paths and Vite proxies them to backend in dev mode.

## Full Stack (Single Server)

```bash
cd frontend
npm run build
cd ..
uvicorn backend.app.main:app --reload
```

Then open `http://localhost:8000` and FastAPI will serve `frontend/dist` plus API routes.

## API Endpoints

- `GET /health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/projects` (auth required)
- `GET /api/v1/projects` (auth required)
- `POST /api/v1/parse`
- `POST /api/v1/generate/sow`
- `POST /api/v1/generate/pptx`
- `GET /api/v1/artifacts` (auth required)
- `GET /api/v1/artifacts/{artifact_name}`

Generated files are written under `backend/output/`.

## Auth And Persistence Notes

- Register/login returns a bearer token.
- If bearer token is sent in `Authorization`, parse and generate responses are persisted into SQLite (`backend/data/app.db`) with project and artifact records.
- Without bearer token, parse/generate still work but run as non-persistent calls for backward compatibility with existing UI flow.

## Parse Error Handling

- Invalid or corrupted `.docx` uploads now return `400` with a validation message instead of `500`.
