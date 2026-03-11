from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ParsedSection(BaseModel):
    heading: str
    body: str


class ParsedDocument(BaseModel):
    filename: str
    file_type: Literal["docx", "txt"]
    title: str
    text: str
    sections: list[ParsedSection]
    word_count: int
    paragraph_count: int


class ParseResponse(BaseModel):
    document: ParsedDocument
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
    llm_provider: Literal["openai", "groq", "azure_openai"] = "openai"


class GeneratePptxRequest(BaseModel):
    deck_title: str = Field(..., min_length=1)
    subtitle: str | None = None
    source_document: DocumentInput
    max_content_slides: int = Field(default=4, ge=2, le=8)
    project_id: int | None = None
    llm_provider: Literal["openai", "groq", "azure_openai"] = "openai"


class GeneratedSection(BaseModel):
    title: str
    paragraphs: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)


class GeneratedSlide(BaseModel):
    title: str
    bullets: list[str] = Field(default_factory=list)


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
