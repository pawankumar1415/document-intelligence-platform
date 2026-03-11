import type {
  GeneratePptxRequest,
  GenerateResult,
  GenerateSowRequest,
  ParseResponse,
} from "../types/app";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const requestJson = async <T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> => {
  const response = await fetch(input, init);

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API Error (${response.status}): ${detail}`);
  }

  return response.json() as Promise<T>;
};

export const parseDocument = async (file: File): Promise<ParseResponse> => {
  const form = new FormData();
  form.append("file", file);

  return requestJson<ParseResponse>(`${API_BASE_URL}/api/v1/parse`, {
    method: "POST",
    body: form,
  });
};

export const generateSow = async (
  payload: GenerateSowRequest,
): Promise<GenerateResult> => {
  return requestJson<GenerateResult>(`${API_BASE_URL}/api/v1/generate/sow`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
};

export const generatePptx = async (
  payload: GeneratePptxRequest,
): Promise<GenerateResult> => {
  return requestJson<GenerateResult>(`${API_BASE_URL}/api/v1/generate/pptx`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
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
