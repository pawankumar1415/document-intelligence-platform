# BSBI Development Technical Spec

## Objective

Implement a working BSBI-branded thin-slice product using:

- `React + Vite + TypeScript` frontend
- `FastAPI` backend
- Local file parsing and generation flow for:
  - `.docx` and `.txt` parsing
  - SOW generation (`.docx`)
  - PPT generation (`.pptx`)

## Delivery Scope

### Frontend

- Replace legacy NDA/Azure UI with product routes:
  - `/dashboard`
  - `/upload`
  - `/generate`
  - `/outputs`
- Apply BSBI branding:
  - BSBI naming in UI copy
  - BSBI logo usage
  - clean light consultancy visual theme with red accent
- Add real integration with local backend:
  - parse upload
  - SOW generation
  - PPT generation
  - artifact download links

### Backend

- Keep existing endpoints:
  - `POST /api/v1/parse`
  - `POST /api/v1/generate/sow`
  - `POST /api/v1/generate/pptx`
- Add:
  - `GET /api/v1/artifacts/{artifact_name}`
- Add CORS support for local Vite dev origin.
- Extend generation response with `artifact_name` and `download_url`.

## API Contracts

### Parse

`POST /api/v1/parse`  
`multipart/form-data` field: `file`

Returns:

- `document.filename`
- `document.file_type`
- `document.title`
- `document.text`
- `document.sections[]`
- `document.word_count`
- `document.paragraph_count`

### Generate SOW

`POST /api/v1/generate/sow`

Body:

- `client_name`
- `project_name`
- `source_document` (parsed document shape)
- `assumptions[]`

### Generate PPT

`POST /api/v1/generate/pptx`

Body:

- `deck_title`
- `subtitle`
- `source_document` (parsed document shape)
- `max_content_slides`

### Generate Response (both)

- `artifact_type`
- `file_path`
- `artifact_name`
- `download_url`
- `summary`
- `sections[]` or `slides[]`

### Artifact Download

`GET /api/v1/artifacts/{artifact_name}`

Returns the generated file stream for direct download.

## UX Flow

1. User lands on Dashboard.
2. User uploads `.docx` or `.txt` on Upload page.
3. Frontend calls parse endpoint and stores parsed document in app state.
4. User visits Generate page and triggers SOW or PPT creation.
5. Frontend stores generation responses as output records.
6. Outputs page lists generated artifacts with download actions.

## Validation And Acceptance Criteria

- Navbar and page copy use BSBI branding.
- Upload accepts only `.docx` and `.txt`.
- Parse response renders summary and extracted sections.
- SOW generation creates downloadable `.docx`.
- PPT generation creates downloadable `.pptx`.
- Outputs page shows artifact metadata and working download actions.
- Legacy NDA/Azure views are removed from app routes and code.
- Backend supports CORS for local frontend.

## Out Of Scope

- Authentication and user management
- Multi-project tenancy and collaboration
- Advanced prompt orchestration or model switching
- Enterprise workflow approvals

## Next Iteration Candidates

- Persist parsed docs and outputs in backend storage
- Replace in-memory frontend state with backend project state
- Add PDF parsing and OCR integration
- Introduce local LLM-backed generation quality improvements
