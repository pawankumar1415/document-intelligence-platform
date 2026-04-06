# Document Intelligence Platform Plan

## 1. Product Summary

The Document Intelligence Platform is an internal web application that accepts uploaded business documents in multiple formats and turns them into structured outputs such as:

- Statement of Work (SOW)
- Proposal documents
- PowerPoint decks

The core idea is:

1. A user creates a project workspace.
2. The user uploads one or more source files such as `pdf`, `docx`, `xlsx`, `txt`, and image-based documents.
3. The platform extracts text, OCR content, and tables from those files.
4. The platform asks guided requirement questions to fill in gaps that the source documents do not answer clearly.
5. The platform generates structured drafts for selected output types.
6. The user reviews and edits the generated content in the app.
7. The platform exports editable output files and stores version history.

This is a generation-first platform, not a general-purpose document chat product in v1.

## 2. Primary Goals

- Support document ingestion across common business file formats
- Extract usable structured content from text, scans, tables, and images
- Generate high-value business deliverables from uploaded documents
- Keep infrastructure cost controlled
- Prefer local execution where practical
- Keep the system compatible with cloud deployment when needed
- Build a pilot-friendly internal product with enterprise baseline controls

## 3. V1 Scope

### Included

- Internal users only
- Manual file upload only
- Project-based organization model
- Guided intake questions before generation
- Output generation for:
  - SOW
  - Proposal document
  - PPT deck
- Structured in-app review and editing
- Regeneration with saved versions
- Export of editable output files plus JSON metadata
- Basic admin console
- Enterprise-ready internal baseline:
  - encrypted storage
  - role-aware access
  - audit logging
  - retention-aware design

### Excluded from V1

- Open-ended document chat
- Multiple enterprise source connectors
- Full browser-based office editor
- Deep governance dashboards
- Full collaborative document history
- User-authored template builder

## 4. Product Decisions Locked So Far

- Primary user for the first release: internal teams
- Delivery model: upload + guided Q&A
- Document understanding depth: text + OCR + tables
- Cloud posture: provider-agnostic
- Security posture: enterprise-ready internal baseline
- Output set for first release: SOW + proposal doc + PPT
- Review model: user reviews and edits in app
- Auth for initial phase: email/password
- Document chat in v1: no, except guided intake Q&A
- Scale target: pilot team scale
- Export requirement: editable files + JSON metadata
- LLM strategy: provider abstraction, OpenAI-first
- Generation mode: async jobs with progress states
- Extraction direction: phased approach with clean abstraction, not a hard custom-only build on day one
- Review experience: structured web editor
- Traceability level: basic source list only
- Workspace model: project workspace
- Template model: admin-managed templates
- Draft handling: regenerate and keep versions
- Connectors in v1: manual upload only
- Admin scope in v1: basic admin console
- Delivery milestone by March 31, 2026: clickable demo
- Initial delivery capacity assumption: 1-2 engineers

## 5. Recommended Product Workflow

### User workflow

1. Log in
2. Create a project
3. Upload one or more source documents
4. Wait for extraction and indexing to complete
5. Answer guided requirement questions
6. Select output type and template
7. Generate a draft
8. Review and edit sections in the web app
9. Regenerate if needed
10. Export the final draft

### Admin workflow

1. Manage users
2. Manage templates
3. Review job health
4. Review audit events
5. Configure retention-related settings

## 6. Suggested Technical Architecture

### Frontend

- React application
- Main areas:
  - login
  - project dashboard
  - upload flow
  - processing status
  - guided Q&A
  - draft editor
  - export flow
  - admin console

### Backend

Use a modular Python backend rather than microservices for the first implementation.

Recommended backend modules:

- Auth and Users
- Projects and Workspaces
- Document Upload and Storage
- Extraction and Normalization
- Chunking and Indexing
- Guided Question Generation
- Draft Generation
- Templates
- Draft Versioning
- Export
- Admin and Audit

### Storage pattern

- Relational database for users, projects, templates, jobs, drafts, and audit data
- Object storage for raw uploaded files and exported files
- Vector database for embeddings and retrieval support

### Job pattern

Use async jobs for:

- OCR and extraction
- table processing
- chunking and indexing
- question generation
- draft generation
- export creation

The platform should show clear job states such as:

- uploaded
- extracting
- indexing
- questioning
- generating
- ready
- failed

## 7. Core Data Objects

### Project

- `id`
- `owner_id`
- `name`
- `status`
- `created_at`

### SourceDocument

- `id`
- `project_id`
- `file_name`
- `file_type`
- `storage_path`
- `extraction_status`
- `metadata`

### ExtractedDocument

- `document_id`
- `normalized_text`
- `table_blocks`
- `image_refs`
- `chunk_refs`

### RequirementAnswerSet

- `project_id`
- `question_set_version`
- `answers_json`

### Template

- `id`
- `output_type`
- `version`
- `schema_json`

### GenerationJob

- `id`
- `project_id`
- `output_type`
- `status`
- `provider`
- `prompt_version`

### DraftArtifact

- `id`
- `project_id`
- `output_type`
- `version_number`
- `structured_content_json`
- `export_paths`

### SourceUsage

- `draft_id`
- `document_ids`

### AuditEvent

- `actor_id`
- `entity_type`
- `entity_id`
- `action`
- `timestamp`

## 8. Backend Framework Recommendation

Based on the current requirements, the recommended backend foundation is:

`FastAPI-first`

### Why FastAPI is the best fit

- Better fit for a React frontend and API-first backend
- Strong fit for async document-processing workflows
- Good match for long-running AI and extraction workloads
- Cleaner integration point for local model serving
- Lower framework overhead than Django for this specific product

### Why not Django-first

Django remains a strong framework, but for this product it is less aligned because:

- the platform is AI-workflow heavy rather than admin/CRUD heavy
- async document processing is central
- the main application surface is a custom React app, not server-rendered views

Django can still be useful later if a heavier built-in admin surface becomes a major requirement, but it is not the best primary backend choice for the current product direction.

## 9. Recommended Low-Cost Local AI Stack

Because local execution and lower cost are preferred, the recommended technical stack around the Python backend is:

`FastAPI + Postgres + Redis-backed worker + Docling + Ollama + Qdrant`

### Role of each part

- `FastAPI`: API layer
- `Postgres`: relational application state
- `Redis-backed worker`: async job execution
- `Docling`: local document parsing and extraction
- `Ollama`: local quantized model runtime
- `Qdrant`: vector storage

### Local-first reasoning

- Use local extraction wherever practical
- Use local quantized generation for first drafts and intermediate summarization
- Keep cloud fallback possible for harder generations if quality later requires it
- Maintain provider abstractions so components can be swapped without rewriting the product

## 10. Document Extraction Strategy

### Short-term approach

- Use a clean extraction abstraction
- Start with pragmatic coverage for common formats
- Support OCR, text extraction, and table-aware processing
- Normalize all extracted output into a common internal representation

### Long-term approach

- Gradually replace individual extraction components if a more custom pipeline is needed
- Avoid locking the system to a single managed extraction dependency

### Internal normalized representation should support

- text blocks
- table blocks
- image references
- source metadata
- chunk references

## 11. Generation Strategy

Generation should be based on:

- source document content
- extracted normalized structure
- guided requirement answers
- output template

This is more reliable than prompting directly from raw uploaded text.

### Output strategy

- SOW -> editable `docx`
- Proposal -> editable `docx`
- Presentation -> editable `pptx`
- JSON metadata stored alongside every draft

## 12. Milestone Plan

### By March 31, 2026

Deliver a clickable demo that shows:

- login flow
- project creation
- upload flow
- visible processing states
- guided Q&A
- one thin end-to-end generation path for either SOW or proposal

PPT generation can be partial or mocked in the demo if needed to keep the milestone realistic.

### Next phase after the clickable demo

- stabilize one real end-to-end output path
- add remaining output types
- improve export fidelity
- add stronger admin tools
- strengthen retries, validation, and monitoring

### Later pilot-hardening phase

- stronger operational monitoring
- quota and retention controls
- improved messy-document handling
- optional SSO
- deeper template management

## 13. Testing Strategy

The platform should be tested across:

- `pdf`, `docx`, `xlsx`, `txt`, and image-based uploads
- OCR and table extraction
- multi-document project handling
- guided Q&A generation
- output generation for each supported output type
- version retention on regeneration
- editable export validity
- role-based permissions
- async job state transitions
- audit logging

## 14. Key Risks and Constraints

### Main risks

- local model quality may be good enough for drafts but not always for final polished outputs
- extraction quality across messy documents can vary significantly
- PPT generation quality is usually harder than document generation
- custom extraction ambitions can expand scope too early
- enterprise security expectations and simple email/password auth can become misaligned

### Practical mitigation

- keep the backend modular
- keep provider boundaries explicit
- avoid overbuilding the first version
- prioritize one high-quality thin slice before broadening scope

## 15. Source References for the Backend Decision

These were the main references used for the backend recommendation and local-first AI stack discussion:

- FastAPI async docs: <https://fastapi.tiangolo.com/async/>
- FastAPI background tasks docs: <https://fastapi.tiangolo.com/tutorial/background-tasks/>
- Django async docs: <https://docs.djangoproject.com/en/6.0/topics/async/>
- Django admin docs: <https://docs.djangoproject.com/en/6.0/ref/contrib/admin/>
- Docling docs: <https://docling-project.github.io/docling/>
- Ollama docs: <https://docs.ollama.com/>
- Ollama import and quantization docs: <https://docs.ollama.com/import>
- Qdrant quickstart docs: <https://qdrant.tech/documentation/quickstart/>
- Haystack Ollama integration docs: <https://docs.haystack.deepset.ai/docs/ollamagenerator>
- Haystack Qdrant integration docs: <https://docs.haystack.deepset.ai/docs/qdrant-document-store>

## 16. Final Working Recommendation

If implementation starts now, the strongest practical default is:

- Build the product as a `React + FastAPI` application
- Keep the backend as a modular monolith at first
- Use async workers for heavy processing
- Prefer `Docling + Ollama + Qdrant` for the local-first AI stack
- Optimize for a clickable demo by March 31, 2026
- After the demo, harden one real thin-slice workflow before expanding feature breadth
