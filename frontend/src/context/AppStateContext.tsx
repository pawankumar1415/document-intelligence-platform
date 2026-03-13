import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { getProviderCatalog, updateEmbeddingConfig } from "../services/api";
import type {
  AuthUser,
  EmbeddingCatalog,
  LLMProvider,
  OutputArtifact,
  ParsedDocument,
  ProviderCatalogEntry,
} from "../types/app";

type AppStateContextValue = {
  parsedDocument: ParsedDocument | null;
  outputs: OutputArtifact[];
  projectId: number | null;
  token: string | null;
  user: AuthUser | null;
  llmProvider: LLMProvider;
  llmModel: string;
  providerCatalog: ProviderCatalogEntry[];
  providerCatalogLoading: boolean;
  providerCatalogError: string | null;
  embeddingCatalog: EmbeddingCatalog | null;
  embeddingUpdateLoading: boolean;
  embeddingUpdateError: string | null;
  setParsedDocument: (document: ParsedDocument | null) => void;
  setProjectId: (projectId: number | null) => void;
  setSession: (token: string, user: AuthUser) => void;
  clearSession: () => void;
  setLlmProvider: (provider: LLMProvider) => void;
  setLlmModel: (provider: LLMProvider, model: string) => void;
  applyEmbeddingConfig: (backend: string, modelId: string) => Promise<void>;
  refreshProviderCatalog: () => Promise<void>;
  addOutput: (artifact: Omit<OutputArtifact, "id" | "created_at">) => void;
  clearAll: () => void;
};

const AppStateContext = createContext<AppStateContextValue | undefined>(undefined);

export const AppStateProvider = ({ children }: { children: ReactNode }) => {
  const [parsedDocument, setParsedDocument] = useState<ParsedDocument | null>(null);
  const [outputs, setOutputs] = useState<OutputArtifact[]>([]);
  const [projectId, setProjectId] = useState<number | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("auth_token"));
  const [user, setUser] = useState<AuthUser | null>(() => {
    const raw = localStorage.getItem("auth_user");
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  });
  const [providerCatalog, setProviderCatalog] = useState<ProviderCatalogEntry[]>([]);
  const [providerCatalogLoading, setProviderCatalogLoading] = useState(false);
  const [providerCatalogError, setProviderCatalogError] = useState<string | null>(null);
  const [embeddingCatalog, setEmbeddingCatalog] = useState<EmbeddingCatalog | null>(null);
  const [embeddingUpdateLoading, setEmbeddingUpdateLoading] = useState(false);
  const [embeddingUpdateError, setEmbeddingUpdateError] = useState<string | null>(null);
  const [llmProvider, setLlmProvider] = useState<LLMProvider>(() => {
    const raw = localStorage.getItem("llm_provider");
    if (raw === "openai" || raw === "groq" || raw === "azure_openai" || raw === "ollama") {
      return raw;
    }
    return "openai";
  });
  const [selectedModels, setSelectedModels] = useState<Record<string, string>>(() => {
    const raw = localStorage.getItem("llm_models");
    if (!raw) {
      return {};
    }
    try {
      return JSON.parse(raw) as Record<string, string>;
    } catch {
      return {};
    }
  });

  const refreshCatalog = async (sessionToken: string): Promise<void> => {
    setProviderCatalogLoading(true);
    setProviderCatalogError(null);
    try {
      const response = await getProviderCatalog({ token: sessionToken });
      const enabledProviders = response.providers.filter((entry) => entry.enabled);
      setProviderCatalog(enabledProviders);
      setEmbeddingCatalog(response.embedding);
      if (enabledProviders.length > 0 && !enabledProviders.some((entry) => entry.provider === llmProvider)) {
        const fallbackProvider = enabledProviders[0].provider;
        setLlmProvider(fallbackProvider);
        localStorage.setItem("llm_provider", fallbackProvider);
      }
      setSelectedModels((current) => {
        const next = { ...current };
        for (const entry of enabledProviders) {
          const configuredModel = next[entry.provider];
          const isConfiguredValid = entry.models.some((model) => model.id === configuredModel);
          if (!configuredModel || !isConfiguredValid) {
            next[entry.provider] = entry.default_model || entry.models[0]?.id || "";
          }
        }
        localStorage.setItem("llm_models", JSON.stringify(next));
        return next;
      });
    } finally {
      setProviderCatalogLoading(false);
    }
  };

  useEffect(() => {
    if (!token) {
      setProviderCatalog([]);
      setEmbeddingCatalog(null);
      setProviderCatalogError(null);
      return;
    }

    let isCancelled = false;
    refreshCatalog(token).catch((error: unknown) => {
      if (isCancelled) {
        return;
      }
      const message = error instanceof Error ? error.message : "Could not load provider catalog.";
      setProviderCatalog([]);
      setEmbeddingCatalog(null);
      setProviderCatalogError(message);
      setProviderCatalogLoading(false);
    });

    return () => {
      isCancelled = true;
    };
  }, [token]);

  const setSession = (nextToken: string, nextUser: AuthUser) => {
    setToken(nextToken);
    setUser(nextUser);
    localStorage.setItem("auth_token", nextToken);
    localStorage.setItem("auth_user", JSON.stringify(nextUser));
  };

  const clearSession = () => {
    setToken(null);
    setUser(null);
    setProjectId(null);
    setParsedDocument(null);
    setOutputs([]);
    setProviderCatalog([]);
    setEmbeddingCatalog(null);
    setProviderCatalogError(null);
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
  };

  const updateLlmProvider = (provider: LLMProvider) => {
    setLlmProvider(provider);
    localStorage.setItem("llm_provider", provider);
  };

  const updateLlmModel = (provider: LLMProvider, model: string) => {
    setSelectedModels((current) => {
      const next = {
        ...current,
        [provider]: model,
      };
      localStorage.setItem("llm_models", JSON.stringify(next));
      return next;
    });
  };

  const applyEmbeddingConfig = async (backend: string, modelId: string) => {
    if (!token) {
      throw new Error("You must be logged in to update embedding configuration.");
    }
    setEmbeddingUpdateLoading(true);
    setEmbeddingUpdateError(null);
    try {
      await updateEmbeddingConfig(
        {
          backend,
          model_id: modelId,
        },
        { token },
      );
      await refreshCatalog(token);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not update embedding configuration.";
      setEmbeddingUpdateError(message);
      throw error;
    } finally {
      setEmbeddingUpdateLoading(false);
    }
  };

  const refreshProviderCatalog = async () => {
    if (!token) {
      throw new Error("You must be logged in to refresh provider catalog.");
    }
    await refreshCatalog(token);
  };

  const addOutput = (artifact: Omit<OutputArtifact, "id" | "created_at">) => {
    const now = new Date().toISOString();
    const record: OutputArtifact = {
      ...artifact,
      id: `${artifact.artifact_name}-${now}`,
      created_at: now,
    };
    setOutputs((current) => [record, ...current]);
  };

  const clearAll = () => {
    setParsedDocument(null);
    setOutputs([]);
    setProjectId(null);
  };

  const activeProviderConfig = providerCatalog.find((entry) => entry.provider === llmProvider);
  const llmModel =
    selectedModels[llmProvider] ||
    activeProviderConfig?.default_model ||
    activeProviderConfig?.models[0]?.id ||
    "";

  const value = useMemo(
    () => ({
      parsedDocument,
      outputs,
      projectId,
      token,
      user,
      llmProvider,
      llmModel,
      providerCatalog,
      providerCatalogLoading,
      providerCatalogError,
      embeddingCatalog,
      embeddingUpdateLoading,
      embeddingUpdateError,
      setParsedDocument,
      setProjectId,
      setSession,
      clearSession,
      setLlmProvider: updateLlmProvider,
      setLlmModel: updateLlmModel,
      applyEmbeddingConfig,
      refreshProviderCatalog,
      addOutput,
      clearAll,
    }),
    [
      embeddingCatalog,
      llmModel,
      llmProvider,
      outputs,
      parsedDocument,
      projectId,
      providerCatalog,
      providerCatalogError,
      providerCatalogLoading,
      embeddingUpdateLoading,
      embeddingUpdateError,
      token,
      user,
    ],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
};

export const useAppState = (): AppStateContextValue => {
  const value = useContext(AppStateContext);
  if (!value) {
    throw new Error("useAppState must be used within AppStateProvider.");
  }
  return value;
};
