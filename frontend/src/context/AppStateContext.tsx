import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import type { AuthUser, LLMProvider, OutputArtifact, ParsedDocument } from "../types/app";

type AppStateContextValue = {
  parsedDocument: ParsedDocument | null;
  outputs: OutputArtifact[];
  projectId: number | null;
  token: string | null;
  user: AuthUser | null;
  llmProvider: LLMProvider;
  setParsedDocument: (document: ParsedDocument | null) => void;
  setProjectId: (projectId: number | null) => void;
  setSession: (token: string, user: AuthUser) => void;
  clearSession: () => void;
  setLlmProvider: (provider: LLMProvider) => void;
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
  const [llmProvider, setLlmProvider] = useState<LLMProvider>(() => {
    const raw = localStorage.getItem("llm_provider");
    if (raw === "openai" || raw === "groq" || raw === "azure_openai") {
      return raw;
    }
    return "openai";
  });

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
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
  };

  const updateLlmProvider = (provider: LLMProvider) => {
    setLlmProvider(provider);
    localStorage.setItem("llm_provider", provider);
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

  const value = useMemo(
    () => ({
      parsedDocument,
      outputs,
      projectId,
      token,
      user,
      llmProvider,
      setParsedDocument,
      setProjectId,
      setSession,
      clearSession,
      setLlmProvider: updateLlmProvider,
      addOutput,
      clearAll,
    }),
    [llmProvider, outputs, parsedDocument, projectId, token, user],
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
