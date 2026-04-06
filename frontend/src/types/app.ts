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
  is_admin?: boolean;
  is_active?: boolean;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type ChatRequest = {
  question: string;
  session_id?: string | null;
  project_id?: number | null;
  llm_provider: LLMProvider;
  llm_model?: string | null;
};

export type ChatResponse = {
  answer: string;
  session_id: string;
  meta: {
    intent: string;
    context_length: number;
    is_new_session: boolean;
  };
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

export type SummaryMode = "executive_summary" | "bullet_points" | "narrative_rewrite" | "key_insights";

export type SummarizeRequest = {
  title: string;
  source_text: string;
  file_type?: string;
  extraction_signals?: ExtractionSignal[];
  mode: SummaryMode;
  llm_provider: LLMProvider;
  llm_model?: string;
};

export type SummaryGroup = {
  heading: string;
  bullets: string[];
};

export type SummaryInsight = {
  insight: string;
  significance: "high" | "medium" | "low";
};

export type SummarizeResponse = {
  mode: SummaryMode;
  doc_context: string;
  title: string;
  paragraphs: string[];
  key_points: string[];
  groups: SummaryGroup[];
  insights: SummaryInsight[];
  summary_line: string;
};

// ── Rubric types ──────────────────────────────────────────────────────────────

export type RubricSeverity = "low" | "medium" | "high";

export type RubricCriterion = {
  id?: number;
  name: string;
  description: string;
  severity: RubricSeverity;
  sort_order: number;
};

export type RubricSummary = {
  id: number;
  name: string;
  description: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export type RubricRecord = RubricSummary & {
  criteria: RubricCriterion[];
};

export type RubricCreateRequest = {
  name: string;
  description: string;
  criteria: RubricCriterion[];
};

// ── Validation types ──────────────────────────────────────────────────────────

export type ValidationVerdict = "PASS" | "PASS_WITH_WARNINGS" | "FAIL" | "ERROR" | "SKIPPED";

export type ValidationLayer1 = {
  compliance_score: number;
  issues: string[];
  passed: string[];
};

export type ValidationLayer2 = {
  consistency_issues: string[];
  passed: string[];
};

export type ValidationMeta = {
  document_name: string;
  rubric_id: number;
  rubric_name: string;
  chunks_used: number;
};

export type ValidationResult = {
  overall_verdict: ValidationVerdict;
  layer1: ValidationLayer1;
  layer2: ValidationLayer2;
  rewritten_text: string;
  meta: ValidationMeta;
};

export type ValidateRequest = {
  text: string;
  document_name: string;
  rubric_id?: number | null;
  llm_provider: LLMProvider;
  llm_model?: string | null;
};

export type BatchValidateResponse = {
  total: number;
  rubric_name: string;
  results: ValidationResult[];
};

// ── SharePoint types ──────────────────────────────────────────────────────────

export type SharePointSite = {
  id: string;
  name: string;
  web_url: string;
};

export type SharePointLibrary = {
  id: string;
  name: string;
  web_url: string;
};

export type SharePointFile = {
  id: string;
  name: string;
  size: number;
  last_modified: string;
  web_url: string;
  mime_type: string;
  is_folder: boolean;
};

export type SharePointFilesResponse = {
  library_id: string;
  folder_path: string;
  items: SharePointFile[];
};
