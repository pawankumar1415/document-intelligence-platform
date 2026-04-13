import type {
  AnalyticsDashboard,
  AuthResponse,
  CaseStudyMetric,
  GenerateCaseStudyRequest,
  BatchValidateResponse,
  ChatRequest,
  ChatResponse,
  ClauseAutoExtractRequest,
  ClauseCreateRequest,
  ClauseRecord,
  ClauseSearchResponse,
  CompareRequest,
  ComparisonResult,
  ExtractionResult,
  ExtractionSchemaCreateRequest,
  ExtractionSchemaRecord,
  ExtractionSchemaSummary,
  ExtractRequest,
  GenerateBidRequest,
  GeneratePptxRequest,
  GenerateResult,
  GenerateSowRequest,
  LLMProvider,
  EmbeddingCatalog,
  ParseResponse,
  ProviderCatalogResponse,
  RubricCreateRequest,
  RubricRecord,
  RubricSummary,
  SharePointLibrary,
  SharePointFilesResponse,
  SharePointSite,
  SummarizeRequest,
  SummarizeResponse,
  UseCaseAssessment,
  ValidateRequest,
  ValidationResult,
} from "../types/app";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "";

export type ApiErrorPayload = {
  code?: string;
  message?: string;
  assessment?: UseCaseAssessment;
};

export class ApiError extends Error {
  status: number;
  payload: ApiErrorPayload | null;

  constructor(status: number, message: string, payload: ApiErrorPayload | null = null) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

const requestJson = async <T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> => {
  const response = await fetch(input, init);

  if (!response.ok) {
    const raw = await response.text();
    let detail = raw;
    let payloadDetail: ApiErrorPayload | null = null;
    try {
      const payload = JSON.parse(raw) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (payload.detail && typeof payload.detail === "object") {
        const detailObject = payload.detail as ApiErrorPayload;
        const reason = detailObject.assessment?.reasons?.[0];
        detail = detailObject.message || reason || JSON.stringify(payload.detail);
        payloadDetail = detailObject;
      }
    } catch {
      detail = raw;
    }
    throw new ApiError(response.status, detail, payloadDetail);
  }

  return response.json() as Promise<T>;
};

type AuthOptions = {
  token: string | null;
};

const authHeaders = (token: string | null) =>
  token ? ({ Authorization: `Bearer ${token}` } as Record<string, string>) : ({} as Record<string, string>);

export const register = async (email: string, password: string): Promise<AuthResponse> => {
  return requestJson<AuthResponse>(`${API_BASE_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });
};

export const login = async (email: string, password: string): Promise<AuthResponse> => {
  return requestJson<AuthResponse>(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });
};

export const parseDocument = async (
  file: File,
  options: AuthOptions & { projectName?: string; llmProvider: LLMProvider; projectId?: number },
): Promise<ParseResponse> => {
  const form = new FormData();
  form.append("file", file);
  form.append("llm_provider", options.llmProvider);
  if (options.projectName) {
    form.append("project_name", options.projectName);
  }
  if (typeof options.projectId === "number") {
    form.append("project_id", String(options.projectId));
  }

  return requestJson<ParseResponse>(`${API_BASE_URL}/api/v1/parse`, {
    method: "POST",
    headers: {
      ...authHeaders(options.token),
    },
    body: form,
  });
};

export const getProviderCatalog = async (options: AuthOptions): Promise<ProviderCatalogResponse> => {
  return requestJson<ProviderCatalogResponse>(`${API_BASE_URL}/api/v1/providers/models`, {
    method: "GET",
    headers: {
      ...authHeaders(options.token),
    },
  });
};

export const updateEmbeddingConfig = async (
  payload: { backend: string; model_id: string },
  options: AuthOptions,
): Promise<EmbeddingCatalog> => {
  return requestJson<EmbeddingCatalog>(`${API_BASE_URL}/api/v1/embedding/config`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(options.token),
    },
    body: JSON.stringify(payload),
  });
};

export const generateSow = async (
  payload: GenerateSowRequest,
  options: AuthOptions,
): Promise<GenerateResult> => {
  return requestJson<GenerateResult>(`${API_BASE_URL}/api/v1/generate/sow`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(options.token),
    },
    body: JSON.stringify(payload),
  });
};

export const generatePptx = async (
  payload: GeneratePptxRequest,
  options: AuthOptions,
): Promise<GenerateResult> => {
  return requestJson<GenerateResult>(`${API_BASE_URL}/api/v1/generate/pptx`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(options.token),
    },
    body: JSON.stringify(payload),
  });
};

export const summarizeDocument = async (
  payload: SummarizeRequest,
  options: AuthOptions,
): Promise<SummarizeResponse> => {
  return requestJson<SummarizeResponse>(`${API_BASE_URL}/api/v1/summarize`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(options.token),
    },
    body: JSON.stringify(payload),
  });
};

export const sendChatMessage = async (
  payload: ChatRequest,
  options: AuthOptions,
): Promise<ChatResponse> => {
  return requestJson<ChatResponse>(`${API_BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(options.token),
    },
    body: JSON.stringify(payload),
  });
};

// ── Rubric API ────────────────────────────────────────────────────────────────

export const listRubrics = async (options: AuthOptions): Promise<RubricSummary[]> => {
  return requestJson<RubricSummary[]>(`${API_BASE_URL}/api/v1/rubrics`, {
    headers: authHeaders(options.token),
  });
};

export const getRubric = async (rubricId: number, options: AuthOptions): Promise<RubricRecord> => {
  return requestJson<RubricRecord>(`${API_BASE_URL}/api/v1/rubrics/${rubricId}`, {
    headers: authHeaders(options.token),
  });
};

export const createRubric = async (
  payload: RubricCreateRequest,
  options: AuthOptions,
): Promise<RubricRecord> => {
  return requestJson<RubricRecord>(`${API_BASE_URL}/api/v1/rubrics`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(options.token) },
    body: JSON.stringify(payload),
  });
};

export const deleteRubric = async (rubricId: number, options: AuthOptions): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/api/v1/rubrics/${rubricId}`, {
    method: "DELETE",
    headers: authHeaders(options.token),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail, null);
  }
};

// ── Validation API ────────────────────────────────────────────────────────────

export const validateDocument = async (
  payload: ValidateRequest,
  options: AuthOptions,
): Promise<ValidationResult> => {
  return requestJson<ValidationResult>(`${API_BASE_URL}/api/v1/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(options.token) },
    body: JSON.stringify(payload),
  });
};

export const validateBatch = async (
  file: File,
  options: AuthOptions & { rubricId?: number | null; llmProvider?: string; llmModel?: string | null },
): Promise<BatchValidateResponse> => {
  const form = new FormData();
  form.append("file", file);
  form.append("llm_provider", options.llmProvider ?? "openai");
  if (options.rubricId != null) form.append("rubric_id", String(options.rubricId));
  if (options.llmModel) form.append("llm_model", options.llmModel);
  return requestJson<BatchValidateResponse>(`${API_BASE_URL}/api/v1/validate/batch`, {
    method: "POST",
    headers: authHeaders(options.token),
    body: form,
  });
};

// ── SharePoint API ────────────────────────────────────────────────────────────

export const getSharePointStatus = async (options: AuthOptions): Promise<{ configured: boolean }> => {
  return requestJson<{ configured: boolean }>(`${API_BASE_URL}/api/v1/sharepoint/status`, {
    headers: authHeaders(options.token),
  });
};

export const getSharePointSites = async (options: AuthOptions): Promise<SharePointSite[]> => {
  return requestJson<SharePointSite[]>(`${API_BASE_URL}/api/v1/sharepoint/sites`, {
    headers: authHeaders(options.token),
  });
};

export const getSharePointLibraries = async (
  siteId: string | null,
  options: AuthOptions,
): Promise<SharePointLibrary[]> => {
  const url = siteId
    ? `${API_BASE_URL}/api/v1/sharepoint/libraries?site_id=${encodeURIComponent(siteId)}`
    : `${API_BASE_URL}/api/v1/sharepoint/libraries`;
  return requestJson<SharePointLibrary[]>(url, { headers: authHeaders(options.token) });
};

export const getSharePointFiles = async (
  libraryId: string,
  folderPath: string,
  options: AuthOptions,
): Promise<SharePointFilesResponse> => {
  const url = `${API_BASE_URL}/api/v1/sharepoint/files?library_id=${encodeURIComponent(libraryId)}&folder_path=${encodeURIComponent(folderPath)}`;
  return requestJson<SharePointFilesResponse>(url, { headers: authHeaders(options.token) });
};

export const sharePointDownloadAndParse = async (
  payload: { library_id: string; item_id: string; filename: string },
  options: AuthOptions & { projectId?: number | null; llmProvider?: string },
): Promise<import("../types/app").ParseResponse> => {
  const params = new URLSearchParams({ llm_provider: options.llmProvider ?? "openai" });
  if (options.projectId != null) params.set("project_id", String(options.projectId));
  return requestJson(`${API_BASE_URL}/api/v1/sharepoint/download-and-parse?${params}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(options.token) },
    body: JSON.stringify(payload),
  });
};

export const downloadArtifactUrl = (downloadUrl: string): string => {
  if (downloadUrl.startsWith("http://") || downloadUrl.startsWith("https://")) {
    return downloadUrl;
  }
  return `${API_BASE_URL}${downloadUrl}`;
};

export const downloadArtifact = async (
  downloadUrl: string,
  artifactName: string,
  options: AuthOptions,
): Promise<void> => {
  const response = await fetch(downloadArtifactUrl(downloadUrl), {
    method: "GET",
    headers: {
      ...authHeaders(options.token),
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail, null);
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = artifactName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
};

// ── Bid API ───────────────────────────────────────────────────────────────────

export const generateBid = async (
  payload: GenerateBidRequest,
  options: AuthOptions,
): Promise<GenerateResult> => {
  return requestJson<GenerateResult>(`${API_BASE_URL}/api/v1/generate/bid`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(options.token) },
    body: JSON.stringify(payload),
  });
};

// ── Comparison API ────────────────────────────────────────────────────────────

export const compareDocuments = async (
  payload: CompareRequest,
  options: AuthOptions,
): Promise<ComparisonResult> => {
  return requestJson<ComparisonResult>(`${API_BASE_URL}/api/v1/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(options.token) },
    body: JSON.stringify(payload),
  });
};

// ── Extraction schema API ─────────────────────────────────────────────────────

export const listExtractionSchemas = async (options: AuthOptions): Promise<ExtractionSchemaSummary[]> => {
  return requestJson<ExtractionSchemaSummary[]>(`${API_BASE_URL}/api/v1/extraction-schemas`, {
    headers: authHeaders(options.token),
  });
};

export const getExtractionSchema = async (schemaId: number, options: AuthOptions): Promise<ExtractionSchemaRecord> => {
  return requestJson<ExtractionSchemaRecord>(`${API_BASE_URL}/api/v1/extraction-schemas/${schemaId}`, {
    headers: authHeaders(options.token),
  });
};

export const createExtractionSchema = async (
  payload: ExtractionSchemaCreateRequest,
  options: AuthOptions,
): Promise<ExtractionSchemaRecord> => {
  return requestJson<ExtractionSchemaRecord>(`${API_BASE_URL}/api/v1/extraction-schemas`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(options.token) },
    body: JSON.stringify(payload),
  });
};

export const deleteExtractionSchema = async (schemaId: number, options: AuthOptions): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/api/v1/extraction-schemas/${schemaId}`, {
    method: "DELETE",
    headers: authHeaders(options.token),
  });
  if (!response.ok) throw new ApiError(response.status, await response.text(), null);
};

export const extractStructuredData = async (
  payload: ExtractRequest,
  options: AuthOptions,
): Promise<ExtractionResult> => {
  return requestJson<ExtractionResult>(`${API_BASE_URL}/api/v1/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(options.token) },
    body: JSON.stringify(payload),
  });
};

// ── Analytics API ─────────────────────────────────────────────────────────────

export const getAnalytics = async (options: AuthOptions): Promise<AnalyticsDashboard> => {
  return requestJson<AnalyticsDashboard>(`${API_BASE_URL}/api/v1/analytics`, {
    headers: authHeaders(options.token),
  });
};

// ── Clause Library API ────────────────────────────────────────────────────────

export const listClauses = async (options: AuthOptions & { projectId?: number | null }): Promise<ClauseRecord[]> => {
  const url = options.projectId
    ? `${API_BASE_URL}/api/v1/clauses?project_id=${options.projectId}`
    : `${API_BASE_URL}/api/v1/clauses`;
  return requestJson<ClauseRecord[]>(url, { headers: authHeaders(options.token) });
};

export const createClause = async (
  payload: ClauseCreateRequest,
  options: AuthOptions,
): Promise<ClauseRecord> => {
  return requestJson<ClauseRecord>(`${API_BASE_URL}/api/v1/clauses`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(options.token) },
    body: JSON.stringify(payload),
  });
};

export const deleteClause = async (clauseId: number, options: AuthOptions): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/api/v1/clauses/${clauseId}`, {
    method: "DELETE",
    headers: authHeaders(options.token),
  });
  if (!response.ok) throw new ApiError(response.status, await response.text(), null);
};

export const searchClauses = async (q: string, options: AuthOptions): Promise<ClauseSearchResponse> => {
  return requestJson<ClauseSearchResponse>(
    `${API_BASE_URL}/api/v1/clauses/search?q=${encodeURIComponent(q)}`,
    { headers: authHeaders(options.token) },
  );
};

export const autoExtractClauses = async (
  payload: ClauseAutoExtractRequest,
  options: AuthOptions,
): Promise<ClauseRecord[]> => {
  return requestJson<ClauseRecord[]>(`${API_BASE_URL}/api/v1/clauses/auto-extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(options.token) },
    body: JSON.stringify(payload),
  });
};

// ── Case Study API ────────────────────────────────────────────────────────────

export const generateCaseStudy = async (
  payload: GenerateCaseStudyRequest,
  options: AuthOptions,
): Promise<GenerateResult> => {
  return requestJson<GenerateResult>(`${API_BASE_URL}/api/v1/generate/case-study`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders(options.token) },
    body: JSON.stringify(payload),
  });
};

