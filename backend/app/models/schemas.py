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


class DocumentInput(BaseModel):
    title: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    sections: list[ParsedSection] = Field(default_factory=list)


class GenerateSowRequest(BaseModel):
    client_name: str = Field(..., min_length=1)
    project_name: str = Field(..., min_length=1)
    source_document: DocumentInput
    assumptions: list[str] = Field(default_factory=list)


class GeneratePptxRequest(BaseModel):
    deck_title: str = Field(..., min_length=1)
    subtitle: str | None = None
    source_document: DocumentInput
    max_content_slides: int = Field(default=4, ge=2, le=8)


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
    sections: list[GeneratedSection] = Field(default_factory=list)
    slides: list[GeneratedSlide] = Field(default_factory=list)
