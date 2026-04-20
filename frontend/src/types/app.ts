export type ParsedSection = {
  heading: string;
  body: string;
};

export type ParsedDocument = {
  filename: string;
  file_type: "docx" | "txt" | "pdf" | "xlsx" | "csv" | "image";
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
  artifact_type: "sow" | "pptx" | "bid" | "register" | "case_study";
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

// ── Comparison types ──────────────────────────────────────────────────────────

export type CompareRequest = {
  doc_a_name: string;
  doc_a_text: string;
  doc_b_name: string;
  doc_b_text: string;
  llm_provider: LLMProvider;
  llm_model?: string | null;
};

export type ComparisonChange = {
  section: string;
  change_type: "added" | "removed" | "improved" | "regressed" | "unchanged";
  details: string;
};

export type ComparisonResult = {
  summary: string;
  overall_sentiment: "improved" | "regressed" | "neutral";
  doc_a_score: number;
  doc_b_score: number;
  key_improvements: string[];
  key_regressions: string[];
  changes: ComparisonChange[];
  doc_a_name: string;
  doc_b_name: string;
};

// ── Extraction types ──────────────────────────────────────────────────────────

export type ExtractionSchemaField = {
  name: string;
  description: string;
  required: boolean;
};

export type ExtractionSchemaSummary = {
  id: number;
  name: string;
  description: string;
  entity_label: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export type ExtractionSchemaRecord = ExtractionSchemaSummary & {
  fields: ExtractionSchemaField[];
};

export type ExtractionSchemaCreateRequest = {
  name: string;
  description: string;
  entity_label: string;
  fields: ExtractionSchemaField[];
};

export type ExtractRequest = {
  document_name: string;
  text: string;
  schema_id: number;
  project_id?: number | null;
  llm_provider: LLMProvider;
  llm_model?: string | null;
};

export type ExtractionResult = {
  schema_name: string;
  entity_label: string;
  field_names: string[];
  rows: string[][];
  artifact_name: string;
  download_url: string;
  total_extracted: number;
};

// ── Analytics types ───────────────────────────────────────────────────────────

export type AnalyticsOverview = {
  total_documents: number;
  total_artifacts: number;
  total_validations: number;
  avg_compliance_score: number;
  pass_rate: number;
  total_clauses: number;
};

export type ValidationTrendPoint = {
  date: string;
  avg_score: number;
  count: number;
  pass_count: number;
};

export type CommonIssue = {
  issue: string;
  count: number;
};

export type ActivityItem = {
  activity_type: "document" | "artifact" | "validation" | "clause";
  name: string;
  created_at: string;
  details: string;
};

export type AnalyticsDashboard = {
  overview: AnalyticsOverview;
  validation_trends: ValidationTrendPoint[];
  common_issues: CommonIssue[];
  recent_activity: ActivityItem[];
};

// ── Clause types ──────────────────────────────────────────────────────────────

export type ClauseRecord = {
  id: number;
  title: string;
  content: string;
  tags: string[];
  source_doc: string;
  project_id?: number | null;
  created_at: string;
};

export type ClauseCreateRequest = {
  title: string;
  content: string;
  tags: string[];
  source_doc: string;
  project_id?: number | null;
};

export type ClauseAutoExtractRequest = {
  document_name: string;
  text: string;
  project_id?: number | null;
  llm_provider: LLMProvider;
  llm_model?: string | null;
};

export type ClauseSearchResponse = {
  query: string;
  results: ClauseRecord[];
};

// ── Case Study types ──────────────────────────────────────────────────────────

export type CaseStudyMetric = {
  label: string;
  value: string;
  description: string;
};

export type GenerateCaseStudyRequest = {
  client_name: string;
  client_industry: string;
  engagement_title: string;
  source_document: DocumentInput;
  challenge_summary: string;
  headline_metrics: CaseStudyMetric[];
  our_approach_points: string[];
  project_id?: number | null;
  llm_provider: LLMProvider;
  llm_model?: string | null;
};

// ── Bid types ─────────────────────────────────────────────────────────────────

export type GenerateBidRequest = {
  client_name: string;
  opportunity_title: string;
  source_document: DocumentInput;
  our_strengths: string[];
  project_id?: number | null;
  llm_provider: LLMProvider;
  llm_model?: string | null;
};

// ── Project types ─────────────────────────────────────────────────────────────

export type ProjectResponse = {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
};

export type ProjectCreateRequest = {
  name: string;
};

// ── Template Library types ────────────────────────────────────────────────────

export type TemplateType = "sow" | "pptx" | "bid" | "case_study";

export type GenerationTemplateSummary = {
  id: number;
  name: string;
  description: string;
  template_type: TemplateType;
  is_default: boolean;
  created_at: string;
};

export type GenerationTemplateRecord = GenerationTemplateSummary & {
  config: Record<string, unknown>;
};

export type GenerationTemplateCreateRequest = {
  name: string;
  description: string;
  template_type: TemplateType;
  config: Record<string, unknown>;
};

// ── Artifact Feedback types ───────────────────────────────────────────────────

export type ArtifactFeedbackRequest = {
  section_title?: string;
  rating: 1 | -1;
  note?: string;
};

export type ArtifactFeedbackRecord = {
  id: number;
  artifact_id: number;
  section_title: string;
  rating: number;
  note: string;
  created_at: string;
};

// ── Share Link types ──────────────────────────────────────────────────────────

export type ShareLinkCreateRequest = {
  expires_in_days?: number | null;
};

export type ShareLinkRecord = {
  token: string;
  artifact_id: number;
  artifact_name: string;
  artifact_type: string;
  download_url: string;
  summary: string;
  created_at: string;
  expires_at: string | null;
};

// ── Project Overview types ────────────────────────────────────────────────────

export type ProjectDocumentSummary = {
  id: number;
  filename: string;
  title: string;
  word_count: number;
  created_at: string;
};

export type ProjectArtifactSummary = {
  id: number;
  artifact_type: string;
  artifact_name: string;
  download_url: string;
  summary: string;
  created_at: string;
};

export type ProjectValidationSummary = {
  id: number;
  document_name: string;
  overall_verdict: string;
  compliance_score: number;
  created_at: string;
};

export type ProjectOverview = {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
  documents: ProjectDocumentSummary[];
  artifacts: ProjectArtifactSummary[];
  recent_validations: ProjectValidationSummary[];
  clause_count: number;
};

export type ValidationDetail = {
  id: number;
  document_name: string;
  overall_verdict: string;
  compliance_score: number;
  rubric_name: string;
  created_at: string;
  layer1: {
    compliance_score: number;
    issues: string[];
    passed: string[];
  };
  layer2: {
    consistency_issues: string[];
    passed: string[];
  };
  rewritten_text: string;
  meta: {
    document_name?: string;
    rubric_name?: string;
    chunks_used?: number;
  };
};
