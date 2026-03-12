import type {
  AuthResponse,
  GeneratePptxRequest,
  GenerateResult,
  GenerateSowRequest,
  LLMProvider,
  ParseResponse,
  ProviderCatalogResponse,
} from "../types/app";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "";

const requestJson = async <T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> => {
  const response = await fetch(input, init);

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API Error (${response.status}): ${detail}`);
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
    throw new Error(`Download failed (${response.status}): ${detail}`);
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
