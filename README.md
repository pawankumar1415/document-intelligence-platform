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
- `POST /api/v1/parse`
- `POST /api/v1/generate/sow`
- `POST /api/v1/generate/pptx`
- `GET /api/v1/artifacts/{artifact_name}`

Generated files are written under `backend/output/`.
