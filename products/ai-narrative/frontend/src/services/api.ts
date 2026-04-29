import type {
  AdminUserRecord,
  AnalyticsDashboard,
  AuthResponse,
  BatchScoreResponse,
  ChatMessage,
  ChatResponse,
  ColumnDetectionResponse,
  DomainProfile,
  EmbeddingCatalog,
  ExtractedRowsResponse,
  ExtractedTextResponse,
  IngestReferenceResponse,
  LLMProvider,
  NarrativeScoreResult,
  ProviderCatalogResponse,
  ReferenceFileRecord,
  RubricRecord,
  RubricSummary,
  SharePointFilesResponse,
  SharePointLibrary,
} from "../types/app";

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string, public payload?: unknown) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, headers: extraHeaders, ...rest } = options;
  const headers: Record<string, string> = {};
  if (!(rest.body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;
  Object.assign(headers, extraHeaders);

  const resp = await fetch(`${BASE}${path}`, { headers, ...rest });
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      const raw = body.detail ?? body;
      detail = typeof raw === "string" ? raw : JSON.stringify(raw);
    } catch {}
    throw new ApiError(resp.status, detail);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export const login = (email: string, password: string) =>
  request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });

export const register = (email: string, password: string) =>
  request<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) });

// ── References ────────────────────────────────────────────────────────────────
export const listReferences = ({ token }: { token: string }) =>
  request<ReferenceFileRecord[]>("/references", { token });

export const ingestReference = async (
  file: File,
  { token, description = "" }: { token: string; description?: string }
): Promise<IngestReferenceResponse> => {
  const form = new FormData();
  form.append("file", file);
  form.append("description", description);
  const resp = await fetch(`${BASE}/references/ingest`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new ApiError(resp.status, body.detail || "Ingest failed.");
  }
  return resp.json();
};

export const deleteReference = (fileId: number, { token }: { token: string }) =>
  request<{ status: string }>(`/references/${fileId}`, { method: "DELETE", token });

// ── Scoring ───────────────────────────────────────────────────────────────────
export const scoreNarrative = (
  body: {
    narrative: string;
    unique_id: string;
    document_name: string;
    rubric_id?: number | null;
    llm_provider: LLMProvider;
    llm_model?: string | null;
    top_k_references?: number;
  },
  { token, signal }: { token: string; signal?: AbortSignal }
) =>
  request<NarrativeScoreResult>("/score", {
    method: "POST",
    token,
    signal,
    body: JSON.stringify(body),
  });

export const scoreBatch = async (
  file: File,
  opts: {
    token: string;
    rubricId?: number | null;
    llmProvider: LLMProvider;
    llmModel?: string | null;
    topKReferences?: number;
    idColumn?: string;
    narrativeColumn?: string;
    signal?: AbortSignal;
  }
): Promise<BatchScoreResponse> => {
  const form = new FormData();
  form.append("file", file);
  if (opts.rubricId != null) form.append("rubric_id", String(opts.rubricId));
  form.append("llm_provider", opts.llmProvider);
  if (opts.llmModel) form.append("llm_model", opts.llmModel);
  if (opts.topKReferences != null) form.append("top_k_references", String(opts.topKReferences));
  if (opts.idColumn) form.append("id_column", opts.idColumn);
  if (opts.narrativeColumn) form.append("narrative_column", opts.narrativeColumn);

  const resp = await fetch(`${BASE}/score/batch`, {
    method: "POST",
    headers: { Authorization: `Bearer ${opts.token}` },
    body: form,
    signal: opts.signal,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    const raw = body.detail ?? body;
    throw new ApiError(resp.status, typeof raw === "string" ? raw : JSON.stringify(raw));
  }
  return resp.json();
};

export const downloadSharePointFile = async (
  libraryId: string,
  itemId: string,
  filename: string,
  { token }: { token: string | null }
): Promise<File> => {
  const qs = new URLSearchParams({ library_id: libraryId, item_id: itemId, filename }).toString();
  const resp = await fetch(`${BASE}/sharepoint/download?${qs}`, {
    headers: { Authorization: `Bearer ${token ?? ""}` },
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    const raw = body.detail ?? body;
    throw new ApiError(resp.status, typeof raw === "string" ? raw : JSON.stringify(raw));
  }
  const blob = await resp.blob();
  return new File([blob], filename, { type: blob.type });
};

// ── Rubrics ───────────────────────────────────────────────────────────────────
export const listRubrics = ({ token }: { token: string }) =>
  request<RubricSummary[]>("/rubrics", { token });

export const createRubric = (
  body: { name: string; description: string; criteria: unknown[] },
  { token }: { token: string }
) =>
  request<RubricRecord>("/rubrics", { method: "POST", token, body: JSON.stringify(body) });

export const deleteRubric = (id: number, { token }: { token: string }) =>
  request<{ status: string }>(`/rubrics/${id}`, { method: "DELETE", token });

// ── Analytics ─────────────────────────────────────────────────────────────────
export const getAnalytics = ({ token }: { token: string }) =>
  request<AnalyticsDashboard>("/analytics", { token });

// ── Providers ─────────────────────────────────────────────────────────────────
export const getProviderCatalog = ({ token }: { token: string }) =>
  request<ProviderCatalogResponse>("/providers/models", { token });

export const getEmbeddingConfig = ({ token }: { token: string }) =>
  request<EmbeddingCatalog>("/embedding/config", { token });

export const updateEmbeddingConfig = (
  body: { backend: string; model_id: string },
  { token }: { token: string }
) =>
  request<EmbeddingCatalog>("/embedding/config", { method: "POST", token, body: JSON.stringify(body) });

// ── Admin ─────────────────────────────────────────────────────────────────────
export const adminListUsers = ({ token }: { token: string }) =>
  request<AdminUserRecord[]>("/admin/users", { token });

export const adminUpdateUser = (
  userId: number,
  body: { is_admin?: boolean; is_active?: boolean },
  { token }: { token: string }
) =>
  request<AdminUserRecord>(`/admin/users/${userId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(body),
  });

export const adminDeleteUser = (userId: number, { token }: { token: string }) =>
  request<{ status: string }>(`/admin/users/${userId}`, { method: "DELETE", token });

// ── Onboarding ────────────────────────────────────────────────────────────────
export const completeOnboarding = ({ token }: { token: string }) =>
  request<{ status: string }>("/user/complete-onboarding", { method: "POST", token });

// ── File text extraction ──────────────────────────────────────────────────────
export const extractTextFromFile = (
  file: File,
  { token }: { token: string | null }
): Promise<ExtractedTextResponse> => {
  const fd = new FormData();
  fd.append("file", file);
  return request<ExtractedTextResponse>("/file/extract-text", {
    method: "POST",
    token: token ?? undefined,
    headers: {},
    body: fd,
  });
};

export const extractRowsFromFile = (
  file: File,
  { token }: { token: string | null }
): Promise<ExtractedRowsResponse> => {
  const fd = new FormData();
  fd.append("file", file);
  return request<ExtractedRowsResponse>("/file/extract-rows", {
    method: "POST",
    token: token ?? undefined,
    headers: {},
    body: fd,
  });
};

export const extractTextFromSharePoint = (
  body: { library_id: string; item_id: string; filename: string },
  { token }: { token: string | null }
): Promise<ExtractedTextResponse> =>
  request<ExtractedTextResponse>("/sharepoint/extract-text", {
    method: "POST",
    token: token ?? undefined,
    body: JSON.stringify(body),
  });

export const extractRowsFromSharePoint = (
  body: { library_id: string; item_id: string; filename: string },
  { token }: { token: string | null }
): Promise<ExtractedRowsResponse> =>
  request<ExtractedRowsResponse>("/sharepoint/extract-rows", {
    method: "POST",
    token: token ?? undefined,
    body: JSON.stringify(body),
  });

// ── SharePoint ────────────────────────────────────────────────────────────────
export const getSharePointStatus = ({ token }: { token: string | null }) =>
  request<{ configured: boolean }>("/sharepoint/status", { token: token ?? undefined });

export const getSharePointLibraries = (
  siteId: string | null,
  { token }: { token: string | null }
): Promise<SharePointLibrary[]> => {
  const qs = siteId ? `?site_id=${encodeURIComponent(siteId)}` : "";
  return request<SharePointLibrary[]>(`/sharepoint/libraries${qs}`, { token: token ?? undefined });
};

export const getSharePointFiles = (
  libraryId: string,
  folderPath: string,
  { token }: { token: string | null }
): Promise<SharePointFilesResponse> =>
  request<SharePointFilesResponse>(
    `/sharepoint/files?library_id=${encodeURIComponent(libraryId)}&folder_path=${encodeURIComponent(folderPath)}`,
    { token: token ?? undefined }
  );

// ── Domain Profile ────────────────────────────────────────────────────────────
export const getDomainProfile = ({ token }: { token: string }) =>
  request<DomainProfile>("/domain/profile", { token });

export const deleteDomainProfile = ({ token }: { token: string }) =>
  request<{ status: string }>("/domain/profile", { method: "DELETE", token });

// ── Column Detection ──────────────────────────────────────────────────────────
// ── Chat ─────────────────────────────────────────────────────────────────────
export const getReferencePeriods = ({ token }: { token: string }) =>
  request<{ periods: string[] }>("/references/periods", { token });

export const sendChatMessage = (
  body: {
    messages: ChatMessage[];
    provider: string;
    model?: string | null;
    top_k?: number;
  },
  { token }: { token: string }
) =>
  request<ChatResponse>("/chat", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });

export const detectColumns = (
  file: File,
  opts: { token: string | null; useLlm?: boolean; llmProvider?: string; llmModel?: string | null }
): Promise<ColumnDetectionResponse> => {
  const fd = new FormData();
  fd.append("file", file);
  const params = new URLSearchParams({ use_llm: String(opts.useLlm ?? false) });
  if (opts.llmProvider) params.set("llm_provider", opts.llmProvider);
  if (opts.llmModel) params.set("llm_model", opts.llmModel);
  return request<ColumnDetectionResponse>(`/columns/detect?${params.toString()}`, {
    method: "POST",
    token: opts.token ?? undefined,
    headers: {},
    body: fd,
  });
};