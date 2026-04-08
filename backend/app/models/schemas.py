from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


LLMProvider = Literal["openai", "groq", "azure_openai", "ollama"]


class ParsedSection(BaseModel):
    heading: str
    body: str


class ExtractionSignal(BaseModel):
    name: str
    score: float
    evidence: list[str] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    filename: str
    file_type: Literal["docx", "txt", "pdf"]
    title: str
    text: str
    sections: list[ParsedSection]
    word_count: int
    paragraph_count: int
    extraction_signals: list[ExtractionSignal] = Field(default_factory=list)


class UseCaseAssessment(BaseModel):
    is_supported: bool
    matched_use_cases: list[str] = Field(default_factory=list)
    confidence: float
    reasons: list[str] = Field(default_factory=list)


class ParseResponse(BaseModel):
    document: ParsedDocument
    use_case_assessment: UseCaseAssessment | None = None
    project_id: int | None = None
    document_id: int | None = None


class DocumentInput(BaseModel):
    title: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    sections: list[ParsedSection] = Field(default_factory=list)


class GenerateSowRequest(BaseModel):
    client_name: str = Field(..., min_length=1)
    project_name: str = Field(..., min_length=1)
    source_document: DocumentInput
    assumptions: list[str] = Field(default_factory=list)
    project_id: int | None = None
    llm_provider: LLMProvider = "openai"
    llm_model: str | None = None


class GeneratePptxRequest(BaseModel):
    deck_title: str = Field(..., min_length=1)
    subtitle: str | None = None
    source_document: DocumentInput
    max_content_slides: int = Field(default=6, ge=3, le=12)
    project_id: int | None = None
    llm_provider: LLMProvider = "openai"
    llm_model: str | None = None


class GeneratedSection(BaseModel):
    title: str
    paragraphs: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    table_rows: list[list[str]] = Field(default_factory=list)


SlideType = Literal["content", "section_divider", "metrics", "two_column", "closing"]


class GeneratedSlide(BaseModel):
    title: str
    bullets: list[str] = Field(default_factory=list)
    slide_type: SlideType = "content"
    left_column: list[str] = Field(default_factory=list)
    right_column: list[str] = Field(default_factory=list)


class GenerateResult(BaseModel):
    artifact_type: Literal["sow", "pptx", "bid", "register"]
    file_path: str
    artifact_name: str
    download_url: str
    summary: str
    artifact_id: int | None = None
    project_id: int | None = None
    sections: list[GeneratedSection] = Field(default_factory=list)
    slides: list[GeneratedSlide] = Field(default_factory=list)


class AuthRegisterRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)


class AuthLoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class AuthUserProfile(BaseModel):
    id: int
    email: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in_seconds: int
    user: AuthUserProfile  # may be AuthUserProfileExtended (subclass) at runtime


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)


class ProjectResponse(BaseModel):
    id: int
    name: str
    created_at: str
    updated_at: str


class ArtifactRecord(BaseModel):
    id: int
    project_id: int
    artifact_type: Literal["sow", "pptx", "bid", "register"]
    artifact_name: str
    download_url: str
    summary: str
    created_at: str


class VectorStatusResponse(BaseModel):
    configured: bool
    embedding_dim: int
    embedding_backend: str
    embedding_model_id: str


class ProviderModelOption(BaseModel):
    id: str
    label: str
    provider: LLMProvider
    is_default: bool = False


class ProviderCatalogEntry(BaseModel):
    provider: LLMProvider
    display_name: str
    enabled: bool
    default_model: str
    models: list[ProviderModelOption] = Field(default_factory=list)
    source: str
    source_message: str | None = None


class EmbeddingModelOption(BaseModel):
    id: str
    label: str
    dimension: int


class EmbeddingCatalog(BaseModel):
    backend: str
    model_id: str
    dimension: int
    supported_models: list[EmbeddingModelOption] = Field(default_factory=list)
    label: str


class ProviderCatalogResponse(BaseModel):
    providers: list[ProviderCatalogEntry] = Field(default_factory=list)
    embedding: EmbeddingCatalog


class EmbeddingConfigUpdateRequest(BaseModel):
    backend: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)


class SummaryGroup(BaseModel):
    heading: str
    bullets: list[str] = Field(default_factory=list)


class SummaryInsight(BaseModel):
    insight: str
    significance: str = "medium"


class SummarizeRequest(BaseModel):
    title: str = Field(..., min_length=1)
    source_text: str = Field(..., min_length=10)
    file_type: str | None = None
    extraction_signals: list[ExtractionSignal] | None = None
    mode: Literal["executive_summary", "bullet_points", "narrative_rewrite", "key_insights"] = "executive_summary"
    llm_provider: LLMProvider = "openai"
    llm_model: str | None = None


class SummarizeResponse(BaseModel):
    mode: str
    doc_context: str
    title: str = ""
    paragraphs: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    groups: list[SummaryGroup] = Field(default_factory=list)
    insights: list[SummaryInsight] = Field(default_factory=list)
    summary_line: str = ""


# ── Chat schemas ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str | None = None
    project_id: int | None = None
    llm_provider: LLMProvider = "openai"
    llm_model: str | None = None


class ChatMeta(BaseModel):
    intent: str
    context_length: int
    is_new_session: bool


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    meta: ChatMeta


# ── Admin schemas ──────────────────────────────────────────────────────────────

class AdminUserRecord(BaseModel):
    id: int
    email: str
    created_at: str
    is_admin: bool
    is_active: bool


class AdminUserUpdateRequest(BaseModel):
    is_admin: bool | None = None
    is_active: bool | None = None


# ── Extended auth profile (with admin flag) ────────────────────────────────────

class AuthUserProfileExtended(AuthUserProfile):
    is_admin: bool = False
    is_active: bool = True


# ── Rubric schemas ─────────────────────────────────────────────────────────────

class RubricCriterion(BaseModel):
    id: int | None = None
    name: str = Field(..., min_length=1)
    description: str = ""
    severity: Literal["low", "medium", "high"] = "medium"
    sort_order: int = 0


class RubricRecord(BaseModel):
    id: int
    name: str
    description: str
    is_default: bool
    created_at: str
    updated_at: str
    criteria: list[RubricCriterion] = Field(default_factory=list)


class RubricSummary(BaseModel):
    id: int
    name: str
    description: str
    is_default: bool
    created_at: str
    updated_at: str


class RubricCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    criteria: list[RubricCriterion] = Field(default_factory=list)


# ── Validation schemas ─────────────────────────────────────────────────────────

ValidationVerdict = Literal["PASS", "PASS_WITH_WARNINGS", "FAIL", "ERROR", "SKIPPED"]


class ValidationLayer1(BaseModel):
    compliance_score: float
    issues: list[str] = Field(default_factory=list)
    passed: list[str] = Field(default_factory=list)


class ValidationLayer2(BaseModel):
    consistency_issues: list[str] = Field(default_factory=list)
    passed: list[str] = Field(default_factory=list)


class ValidationMeta(BaseModel):
    document_name: str
    rubric_id: int
    rubric_name: str
    chunks_used: int = 0


class ValidationResult(BaseModel):
    overall_verdict: ValidationVerdict
    layer1: ValidationLayer1
    layer2: ValidationLayer2
    rewritten_text: str = ""
    meta: ValidationMeta


class ValidateRequest(BaseModel):
    text: str = Field(..., min_length=10)
    document_name: str = Field(..., min_length=1)
    rubric_id: int | None = None
    llm_provider: LLMProvider = "openai"
    llm_model: str | None = None


class BatchValidateItem(BaseModel):
    document_name: str
    text: str


class BatchValidateRequest(BaseModel):
    items: list[BatchValidateItem] = Field(default_factory=list)
    rubric_id: int | None = None
    llm_provider: LLMProvider = "openai"
    llm_model: str | None = None


class BatchValidateResult(ValidationResult):
    pass  # same shape, named separately for clarity


class BatchValidateResponse(BaseModel):
    total: int
    rubric_name: str
    results: list[BatchValidateResult] = Field(default_factory=list)


# ── SharePoint schemas ─────────────────────────────────────────────────────────

class SharePointSite(BaseModel):
    id: str
    name: str
    web_url: str


class SharePointLibrary(BaseModel):
    id: str
    name: str
    web_url: str


class SharePointFile(BaseModel):
    id: str
    name: str
    size: int
    last_modified: str
    web_url: str
    mime_type: str = ""
    is_folder: bool = False


class SharePointFilesResponse(BaseModel):
    library_id: str
    folder_path: str
    items: list[SharePointFile] = Field(default_factory=list)


class SharePointDownloadRequest(BaseModel):
    library_id: str
    item_id: str
    filename: str


# ── Comparison schemas ─────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    doc_a_name: str = Field(..., min_length=1)
    doc_a_text: str = Field(..., min_length=10)
    doc_b_name: str = Field(..., min_length=1)
    doc_b_text: str = Field(..., min_length=10)
    llm_provider: LLMProvider = "openai"
    llm_model: str | None = None


class ComparisonChange(BaseModel):
    section: str
    change_type: Literal["added", "removed", "improved", "regressed", "unchanged"]
    details: str


class ComparisonResult(BaseModel):
    summary: str
    overall_sentiment: Literal["improved", "regressed", "neutral"]
    doc_a_score: float
    doc_b_score: float
    key_improvements: list[str] = Field(default_factory=list)
    key_regressions: list[str] = Field(default_factory=list)
    changes: list[ComparisonChange] = Field(default_factory=list)
    doc_a_name: str = ""
    doc_b_name: str = ""


# ── Structured Extractor schemas ───────────────────────────────────────────────

class ExtractionSchemaField(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    required: bool = True


class ExtractionSchemaRecord(BaseModel):
    id: int
    name: str
    description: str
    entity_label: str
    fields: list[ExtractionSchemaField] = Field(default_factory=list)
    is_default: bool = False
    created_at: str
    updated_at: str


class ExtractionSchemaSummary(BaseModel):
    id: int
    name: str
    description: str
    entity_label: str
    is_default: bool
    created_at: str
    updated_at: str


class ExtractionSchemaCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    entity_label: str = Field(..., min_length=1)
    fields: list[ExtractionSchemaField] = Field(default_factory=list)


class ExtractRequest(BaseModel):
    document_name: str = Field(..., min_length=1)
    text: str = Field(..., min_length=10)
    schema_id: int
    project_id: int | None = None
    llm_provider: LLMProvider = "openai"
    llm_model: str | None = None


class ExtractionResult(BaseModel):
    schema_name: str
    entity_label: str
    field_names: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    artifact_name: str
    download_url: str
    total_extracted: int = 0


# ── Analytics schemas ──────────────────────────────────────────────────────────

class AnalyticsOverview(BaseModel):
    total_documents: int = 0
    total_artifacts: int = 0
    total_validations: int = 0
    avg_compliance_score: float = 0.0
    pass_rate: float = 0.0
    total_clauses: int = 0


class ValidationTrendPoint(BaseModel):
    date: str
    avg_score: float
    count: int
    pass_count: int


class CommonIssue(BaseModel):
    issue: str
    count: int


class ActivityItem(BaseModel):
    activity_type: Literal["document", "artifact", "validation", "clause"]
    name: str
    created_at: str
    details: str = ""


class AnalyticsDashboard(BaseModel):
    overview: AnalyticsOverview
    validation_trends: list[ValidationTrendPoint] = Field(default_factory=list)
    common_issues: list[CommonIssue] = Field(default_factory=list)
    recent_activity: list[ActivityItem] = Field(default_factory=list)


# ── Clause Library schemas ─────────────────────────────────────────────────────

class ClauseRecord(BaseModel):
    id: int
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    source_doc: str = ""
    project_id: int | None = None
    created_at: str


class ClauseCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=10)
    tags: list[str] = Field(default_factory=list)
    source_doc: str = ""
    project_id: int | None = None


class ClauseAutoExtractRequest(BaseModel):
    document_name: str = Field(..., min_length=1)
    text: str = Field(..., min_length=50)
    project_id: int | None = None
    llm_provider: LLMProvider = "openai"
    llm_model: str | None = None


class ClauseSearchResponse(BaseModel):
    query: str
    results: list[ClauseRecord] = Field(default_factory=list)


# ── Bid / Proposal schemas ─────────────────────────────────────────────────────

class GenerateBidRequest(BaseModel):
    client_name: str = Field(..., min_length=1)
    opportunity_title: str = Field(..., min_length=1)
    source_document: DocumentInput
    our_strengths: list[str] = Field(default_factory=list)
    project_id: int | None = None
    llm_provider: LLMProvider = "openai"
    llm_model: str | None = None
