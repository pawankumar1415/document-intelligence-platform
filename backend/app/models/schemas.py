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
    artifact_type: Literal["sow", "pptx"]
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
    user: AuthUserProfile


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
    artifact_type: Literal["sow", "pptx"]
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
