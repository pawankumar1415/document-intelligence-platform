"""Pydantic schemas for AI Narrative Search API."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field


# ── Auth ─────────────────────────────────────────────────────────────────────

class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthRegisterRequest(BaseModel):
    email: str
    password: str


class AuthUser(BaseModel):
    id: int
    email: str
    is_admin: bool
    is_active: bool
    onboarding_completed: bool = False


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUser


# ── Reference Files ──────────────────────────────────────────────────────────

class ReferenceFileRecord(BaseModel):
    id: int
    filename: str
    record_count: int
    indexed_at: str
    description: Optional[str] = None


class IngestReferenceResponse(BaseModel):
    status: str
    filename: str
    record_count: int
    skipped: int
    message: str


# ── Rubrics ──────────────────────────────────────────────────────────────────

class RubricCriterion(BaseModel):
    name: str
    description: str
    severity: Literal["low", "medium", "high"] = "medium"


class RubricCreateRequest(BaseModel):
    name: str
    description: str = ""
    criteria: list[RubricCriterion]


class RubricSummary(BaseModel):
    id: int
    name: str
    description: str
    criteria_count: int
    is_default: bool


class RubricRecord(BaseModel):
    id: int
    name: str
    description: str
    criteria: list[RubricCriterion]
    is_default: bool


# ── Scoring ──────────────────────────────────────────────────────────────────

class ScoreRequest(BaseModel):
    narrative: str = Field(..., min_length=10, description="The narrative text to score")
    unique_id: str = Field(..., min_length=1, description="Unique identifier for this narrative")
    document_name: str = Field(..., min_length=1, description="Human-readable document/project name")
    rubric_id: Optional[int] = None
    llm_provider: Literal["openai", "groq", "azure_openai", "ollama"] = "openai"
    llm_model: Optional[str] = None
    top_k_references: int = Field(default=5, ge=1, le=20)


class AbnormalityFlag(BaseModel):
    type: Literal["missing_information", "unusual_claim", "data_discrepancy", "structural", "tone"]
    description: str
    severity: Literal["low", "medium", "high"]
    evidence: str = ""


class Layer1Result(BaseModel):
    compliance_score: float
    issues: list[str]
    passed: list[str]


class Layer2Result(BaseModel):
    abnormalities: list[AbnormalityFlag]
    reference_quality_score: float
    patterns_followed: list[str]
    references_used: int


class NarrativeScoreResult(BaseModel):
    overall_verdict: Literal["PASS", "PASS_WITH_WARNINGS", "FAIL", "SKIPPED", "ERROR"]
    layer1: Layer1Result
    layer2: Layer2Result
    rewritten_narrative: str = ""
    meta: dict


# ── Batch Scoring ─────────────────────────────────────────────────────────────

class BatchScoreResponse(BaseModel):
    total: int
    pass_count: int
    warn_count: int
    fail_count: int
    skip_count: int
    rubric_name: str
    results: list[NarrativeScoreResult]


# ── Analytics ─────────────────────────────────────────────────────────────────

class ScoreOverview(BaseModel):
    total_scored: int
    pass_count: int
    warn_count: int
    fail_count: int
    avg_compliance_score: float
    reference_files_count: int


class RecentScoreItem(BaseModel):
    id: int
    unique_id: str
    document_name: str
    overall_verdict: str
    compliance_score: float
    created_at: str


class AnalyticsDashboard(BaseModel):
    overview: ScoreOverview
    recent_scores: list[RecentScoreItem]


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminUserRecord(BaseModel):
    id: int
    email: str
    is_admin: bool
    is_active: bool
    created_at: str
    score_count: int = 0


class AdminUserUpdateRequest(BaseModel):
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


# ── Provider / Embedding ──────────────────────────────────────────────────────

class ModelEntry(BaseModel):
    id: str
    label: str
    provider: str
    is_default: bool


class ProviderEntry(BaseModel):
    provider: str
    display_name: str
    enabled: bool
    default_model: str
    models: list[ModelEntry]


class ProviderCatalogResponse(BaseModel):
    providers: list[ProviderEntry]


class EmbeddingConfigRequest(BaseModel):
    backend: Literal["huggingface_local", "ollama"]
    model_id: str


class EmbeddingModelEntry(BaseModel):
    id: str
    label: str
    dimension: int


class EmbeddingCatalog(BaseModel):
    backend: str
    model_id: str
    dimension: int
    supported_models: list[EmbeddingModelEntry]


# ── SharePoint ────────────────────────────────────────────────────────────────

class SharePointFile(BaseModel):
    id: str
    name: str
    size: int
    last_modified: str
    web_url: str
    mime_type: str = ""
    is_folder: bool = False


class SharePointLibrary(BaseModel):
    id: str
    name: str
    web_url: str


class SharePointFilesResponse(BaseModel):
    library_id: str
    folder_path: str
    items: list[SharePointFile] = Field(default_factory=list)


class SharePointExtractRequest(BaseModel):
    library_id: str
    item_id: str
    filename: str


class ExtractedTextResponse(BaseModel):
    filename: str
    text: str
    char_count: int


# ── Column Detection ──────────────────────────────────────────────────────────

class ColumnCandidate(BaseModel):
    name: str
    confidence: float
    sample: list[str] = Field(default_factory=list)


class ColumnDetectionResponse(BaseModel):
    all_columns: list[str]
    id_column: Optional[str] = None
    narrative_column: Optional[str] = None
    id_candidates: list[ColumnCandidate] = Field(default_factory=list)
    narrative_candidates: list[ColumnCandidate] = Field(default_factory=list)
    method: str = "heuristic"
    ambiguous: bool = False


# ── Excel Row Extraction ──────────────────────────────────────────────────────

class ExcelRowRecord(BaseModel):
    id: str
    narrative: str


class ExtractedRowsResponse(BaseModel):
    filename: str
    id_column: str
    narrative_column: str
    rows: list[ExcelRowRecord]


# ── Domain Profile ───────────────────────────────────────────────────────────

class DomainProfile(BaseModel):
    domain_name: Optional[str] = None
    period_label: str = "Period"
    period_format: Optional[str] = None
    status_codes: dict = Field(default_factory=dict)
    key_terms: dict = Field(default_factory=dict)
    suggested_questions: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    updated_at: Optional[str] = None


# ── Chat ─────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    provider: str = "openai"
    model: Optional[str] = None
    top_k: int = Field(default=6, ge=1, le=20)


class ChatSource(BaseModel):
    unique_id: str
    excerpt: str
    score: float


class ChatResponse(BaseModel):
    reply: str
    sources: list[ChatSource]
