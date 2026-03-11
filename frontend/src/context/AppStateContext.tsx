import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import type { OutputArtifact, ParsedDocument } from "../types/app";

type AppStateContextValue = {
  parsedDocument: ParsedDocument | null;
  outputs: OutputArtifact[];
  setParsedDocument: (document: ParsedDocument | null) => void;
  addOutput: (artifact: Omit<OutputArtifact, "id" | "created_at">) => void;
  clearAll: () => void;
};

const AppStateContext = createContext<AppStateContextValue | undefined>(undefined);

export const AppStateProvider = ({ children }: { children: ReactNode }) => {
  const [parsedDocument, setParsedDocument] = useState<ParsedDocument | null>(null);
  const [outputs, setOutputs] = useState<OutputArtifact[]>([]);

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
  };

  const value = useMemo(
    () => ({
      parsedDocument,
      outputs,
      setParsedDocument,
      addOutput,
      clearAll,
    }),
    [outputs, parsedDocument],
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
