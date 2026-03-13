export type ParsedSection = {
  heading: string;
  body: string;
};

export type ParsedDocument = {
  filename: string;
  file_type: "docx" | "txt" | "pdf";
  title: string;
  text: string;
  sections: ParsedSection[];
  word_count: number;
  paragraph_count: number;
  extraction_signals?: ExtractionSignal[];
};

export type ParseResponse = {
  document: ParsedDocument;
  use_case_assessment?: UseCaseAssessment;
  project_id?: number;
  document_id?: number;
};

export type UseCaseAssessment = {
  is_supported: boolean;
  matched_use_cases: string[];
  confidence: number;
  reasons: string[];
};

export type ExtractionSignal = {
  name: string;
  score: number;
  evidence: string[];
};

export type DocumentInput = {
  title: string;
  text: string;
  sections: ParsedSection[];
};

export type GenerateSowRequest = {
  client_name: string;
  project_name: string;
  source_document: DocumentInput;
  assumptions: string[];
  project_id?: number;
  llm_provider: LLMProvider;
  llm_model?: string;
};

export type GeneratePptxRequest = {
  deck_title: string;
  subtitle?: string;
  source_document: DocumentInput;
  max_content_slides: number;
  project_id?: number;
  llm_provider: LLMProvider;
  llm_model?: string;
};

export type LLMProvider = "openai" | "groq" | "azure_openai" | "ollama";

export type GeneratedSection = {
  title: string;
  paragraphs: string[];
  bullets: string[];
};

export type GeneratedSlide = {
  title: string;
  bullets: string[];
};

export type GenerateResult = {
  artifact_type: "sow" | "pptx";
  file_path: string;
  artifact_name: string;
  download_url: string;
  summary: string;
  artifact_id?: number;
  project_id?: number;
  sections: GeneratedSection[];
  slides: GeneratedSlide[];
};

export type OutputArtifact = GenerateResult & {
  id: string;
  created_at: string;
};

export type AuthUser = {
  id: number;
  email: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in_seconds: number;
  user: AuthUser;
};

export type ProviderModelOption = {
  id: string;
  label: string;
  provider: LLMProvider;
  is_default: boolean;
};

export type ProviderCatalogEntry = {
  provider: LLMProvider;
  display_name: string;
  enabled: boolean;
  default_model: string;
  models: ProviderModelOption[];
  source: string;
  source_message?: string | null;
};

export type EmbeddingModelOption = {
  id: string;
  label: string;
  dimension: number;
};

export type EmbeddingCatalog = {
  backend: string;
  model_id: string;
  dimension: number;
  supported_models: EmbeddingModelOption[];
  label: string;
};

export type ProviderCatalogResponse = {
  providers: ProviderCatalogEntry[];
  embedding: EmbeddingCatalog;
};
