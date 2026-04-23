import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { AuthUser, EmbeddingCatalog, LLMProvider, ProviderCatalogResponse, RubricSummary } from "../types/app";
import { getEmbeddingConfig, getProviderCatalog, listRubrics, updateEmbeddingConfig } from "../services/api";

interface AppState {
  token: string;
  user: AuthUser | null;
  llmProvider: LLMProvider;
  llmModel: string | null;
  providerCatalog: ProviderCatalogResponse | null;
  embeddingCatalog: EmbeddingCatalog | null;
  rubrics: RubricSummary[];
  setSession: (token: string, user: AuthUser) => void;
  clearSession: () => void;
  setUser: (user: AuthUser) => void;
  setProvider: (provider: LLMProvider, model: string | null) => void;
  refreshProviderCatalog: () => Promise<void>;
  refreshRubrics: () => Promise<void>;
  applyEmbeddingConfig: (backend: string, modelId: string) => Promise<EmbeddingCatalog>;
}

const AppStateContext = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string>(() => localStorage.getItem("an_token") || "");
  const [user, setUser] = useState<AuthUser | null>(() => {
    const raw = localStorage.getItem("an_user");
    return raw ? JSON.parse(raw) : null;
  });
  const [llmProvider, setLlmProvider] = useState<LLMProvider>("openai");
  const [llmModel, setLlmModel] = useState<string | null>(null);
  const [providerCatalog, setProviderCatalog] = useState<ProviderCatalogResponse | null>(null);
  const [embeddingCatalog, setEmbeddingCatalog] = useState<EmbeddingCatalog | null>(null);
  const [rubrics, setRubrics] = useState<RubricSummary[]>([]);

  const setSession = useCallback((tok: string, usr: AuthUser) => {
    setToken(tok);
    setUser(usr);
    localStorage.setItem("an_token", tok);
    localStorage.setItem("an_user", JSON.stringify(usr));
  }, []);

  const clearSession = useCallback(() => {
    setToken("");
    setUser(null);
    localStorage.removeItem("an_token");
    localStorage.removeItem("an_user");
  }, []);

  const setProvider = useCallback((provider: LLMProvider, model: string | null) => {
    setLlmProvider(provider);
    setLlmModel(model);
  }, []);

  const refreshProviderCatalog = useCallback(async () => {
    if (!token) return;
    try {
      const catalog = await getProviderCatalog({ token });
      setProviderCatalog(catalog);
      const embCatalog = await getEmbeddingConfig({ token });
      setEmbeddingCatalog(embCatalog);
    } catch {}
  }, [token]);

  const refreshRubrics = useCallback(async () => {
    if (!token) return;
    try {
      const data = await listRubrics({ token });
      setRubrics(data);
    } catch {}
  }, [token]);

  const applyEmbeddingConfig = useCallback(
    async (backend: string, modelId: string): Promise<EmbeddingCatalog> => {
      const result = await updateEmbeddingConfig({ backend, model_id: modelId }, { token });
      setEmbeddingCatalog(result);
      return result;
    },
    [token]
  );

  useEffect(() => {
    if (token) {
      void refreshProviderCatalog();
      void refreshRubrics();
    }
  }, [token]);

  return (
    <AppStateContext.Provider
      value={{
        token,
        user,
        llmProvider,
        llmModel,
        providerCatalog,
        embeddingCatalog,
        rubrics,
        setSession,
        clearSession,
        setUser,
        setProvider,
        refreshProviderCatalog,
        refreshRubrics,
        applyEmbeddingConfig,
      }}
    >
      {children}
    </AppStateContext.Provider>
  );
}

export function useAppState(): AppState {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used within AppStateProvider");
  return ctx;
}