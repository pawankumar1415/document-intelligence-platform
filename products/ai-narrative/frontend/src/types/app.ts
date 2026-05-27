// ── Auth ─────────────────────────────────────────────────────────────────────
export interface AuthUser {
  id: number;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  onboarding_completed: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

// ── Reference Files ──────────────────────────────────────────────────────────
export interface ReferenceFileRecord {
  id: number;
  filename: string;
  description: string;
  record_count: number;
  indexed_at: string;
}

export interface IngestReferenceResponse {
  status: string;
  filename: string;
  record_count: number;
  skipped: number;
  message: string;
}

// ── Rubrics ──────────────────────────────────────────────────────────────────
export interface RubricCriterion {
  name: string;
  description: string;
  severity: "low" | "medium" | "high";
}

export interface RubricSummary {
  id: number;
  name: string;
  description: string;
  criteria_count: number;
  is_default: boolean;
}

export interface RubricRecord {
  id: number;
  name: string;
  description: string;
  criteria: RubricCriterion[];
  is_default: boolean;
}

// ── Scoring ──────────────────────────────────────────────────────────────────
export type ScoringVerdict = "PASS" | "PASS_WITH_WARNINGS" | "FAIL" | "SKIPPED" | "ERROR";
export type LLMProvider = "openai" | "groq" | "azure_openai" | "ollama";
export type AbnormalityType = "missing_information" | "unusual_claim" | "data_discrepancy" | "structural" | "tone";

export interface AbnormalityFlag {
  type: AbnormalityType;
  description: string;
  severity: "low" | "medium" | "high";
  evidence: string;
}

export interface Layer1Result {
  compliance_score: number;
  issues: string[];
  passed: string[];
}

export interface Layer2Result {
  abnormalities: AbnormalityFlag[];
  reference_quality_score: number;
  patterns_followed: string[];
  references_used: number;
}

export type DiscrepancyType = "cost_overrun" | "cost_underrun" | "schedule_slip" | "data_conflict" | "missing_reference";

export interface Layer3Discrepancy {
  type: DiscrepancyType;
  description: string;
  severity: "low" | "medium" | "high";
  narrative_claim: string;
  data_value: string;
}

export interface Layer3Result {
  discrepancies: Layer3Discrepancy[];
  financial_alignment_score: number;
  aligned_items: string[];
  financial_record_found: boolean;
}

export interface NarrativeScoreResult {
  overall_verdict: ScoringVerdict;
  layer1: Layer1Result;
  layer2: Layer2Result;
  layer3: Layer3Result | null;
  rewritten_narrative: string;
  meta: {
    unique_id: string;
    document_name: string;
    rubric_id: number;
    rubric_name: string;
    references_used: number;
    provider: string;
    model_name?: string;
    has_custom_rules?: boolean;
    has_financial_data?: boolean;
    prompt_hash?: string;
  };
}

export interface BatchScoreResponse {
  total: number;
  pass_count: number;
  warn_count: number;
  fail_count: number;
  skip_count: number;
  rubric_name: string;
  results: NarrativeScoreResult[];
}

// ── Analytics ─────────────────────────────────────────────────────────────────
export interface ScoreOverview {
  total_scored: number;
  pass_count: number;
  warn_count: number;
  fail_count: number;
  avg_compliance_score: number;
  reference_files_count: number;
}

export interface RecentScoreItem {
  id: number;
  unique_id: string;
  document_name: string;
  overall_verdict: ScoringVerdict;
  compliance_score: number;
  created_at: string;
}

export interface AnalyticsDashboard {
  overview: ScoreOverview;
  recent_scores: RecentScoreItem[];
}

// ── Admin ─────────────────────────────────────────────────────────────────────
export interface AdminUserRecord {
  id: number;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
  score_count: number;
}

// ── Providers ─────────────────────────────────────────────────────────────────
export interface ModelEntry {
  id: string;
  label: string;
  provider: string;
  is_default: boolean;
}

export interface ProviderEntry {
  provider: string;
  display_name: string;
  enabled: boolean;
  default_model: string;
  models: ModelEntry[];
}

export interface ProviderCatalogResponse {
  providers: ProviderEntry[];
}

export interface EmbeddingModelEntry {
  id: string;
  label: string;
  dimension: number;
}

export interface EmbeddingCatalog {
  backend: string;
  model_id: string;
  dimension: number;
  supported_models: EmbeddingModelEntry[];
}

// ── SharePoint ────────────────────────────────────────────────────────────────
export interface SharePointFile {
  id: string;
  name: string;
  size: number;
  last_modified: string;
  web_url: string;
  mime_type: string;
  is_folder: boolean;
}

export interface SharePointLibrary {
  id: string;
  name: string;
  web_url: string;
}

export interface SharePointFilesResponse {
  library_id: string;
  folder_path: string;
  items: SharePointFile[];
}

export interface ExtractedTextResponse {
  filename: string;
  text: string;
  char_count: number;
}

// ── Column Detection ──────────────────────────────────────────────────────────
export interface ColumnCandidate {
  name: string;
  confidence: number;
  sample: string[];
}

export interface ColumnDetectionResponse {
  all_columns: string[];
  id_column: string | null;
  narrative_column: string | null;
  id_candidates: ColumnCandidate[];
  narrative_candidates: ColumnCandidate[];
  method: string;
  ambiguous: boolean;
}

// ── Excel Row Extraction ──────────────────────────────────────────────────────
export interface ExcelRowRecord {
  id: string;
  narrative: string;
}

export interface ExtractedRowsResponse {
  filename: string;
  id_column: string;
  narrative_column: string;
  rows: ExcelRowRecord[];
}

// ── Domain Profile ────────────────────────────────────────────────────────────
export interface DomainProfile {
  domain_name: string | null;
  period_label: string;
  period_format: string | null;
  status_codes: Record<string, string>;
  key_terms: Record<string, string>;
  suggested_questions: string[];
  confidence: number;
  updated_at: string | null;
}

// ── Chat ─────────────────────────────────────────────────────────────────────
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatSource {
  unique_id: string;
  excerpt: string;
  score: number;
}

export interface ChatResponse {
  reply: string;
  sources: ChatSource[];
}

// ── Standards ─────────────────────────────────────────────────────────────────
export interface RulesUploadStatus {
  active: boolean;
  rubric_id: number | null;
  rubric_name: string | null;
  criteria_count: number;
  source_filename: string | null;
}

export interface FinancialUploadStatus {
  active: boolean;
  filename: string | null;
  record_count: number;
  uploaded_at: string | null;
}

export interface StandardsStatus {
  rules: RulesUploadStatus;
  financial: FinancialUploadStatus;
}

export interface RulesUploadResponse {
  status: string;
  rubric_id: number;
  criteria_count: number;
  filename: string;
  message: string;
}

export interface FinancialUploadResponse {
  status: string;
  filename: string;
  record_count: number;
  message: string;
}

// ── Drift / Audit ─────────────────────────────────────────────────────────────
export interface DriftDataPoint {
  date: string;
  avg_score: number | null;
  pass_count: number;
  warn_count: number;
  fail_count: number;
  total: number;
  primary_provider: string | null;
}

export interface ProviderChange {
  date: string;
  from_provider: string;
  to_provider: string;
}

export interface DriftMetrics {
  period_days: number;
  total_scored: number;
  data_points: DriftDataPoint[];
  provider_changes: ProviderChange[];
  score_variance: number;
  trend_direction: "improving" | "declining" | "stable";
  model_distribution: Record<string, number>;
  avg_score: number;
  custom_rules_usage_pct: number;
  financial_check_usage_pct: number;
}