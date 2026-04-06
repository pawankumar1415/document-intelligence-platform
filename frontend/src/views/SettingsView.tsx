import { CheckCircle2, Cpu, Layers, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import { useAppState } from "../context/AppStateContext";
import type { LLMProvider } from "../types/app";

const EMBEDDING_BACKEND_OPTIONS = [
  { id: "ollama",            label: "Ollama (local)" },
  { id: "huggingface_local", label: "Hugging Face (local)" },
];

const HUGGINGFACE_MODEL_OPTIONS = [
  { id: "nomic-ai/nomic-embed-text-v1.5",              label: "Nomic Embed Text v1.5",    dimension: 768  },
  { id: "BAAI/bge-m3",                                 label: "BGE-M3",                   dimension: 1024 },
  { id: "intfloat/multilingual-e5-large-instruct",     label: "Multilingual E5 Large",    dimension: 1024 },
];

const OLLAMA_MODEL_OPTIONS = [
  { id: "qwen3-embedding:0.6b",  label: "qwen3-embedding:0.6b",  dimension: 1024 },
  { id: "qwen3-embedding:4b",    label: "qwen3-embedding:4b",    dimension: 2560 },
  { id: "nomic-embed-text",      label: "nomic-embed-text",      dimension: 768  },
  { id: "mxbai-embed-large",     label: "mxbai-embed-large",     dimension: 1024 },
  { id: "bge-m3",                label: "bge-m3",                dimension: 1024 },
  { id: "all-minilm",            label: "all-minilm",            dimension: 384  },
];

const SettingsView = () => {
  const {
    llmProvider,
    llmModel,
    providerCatalog,
    providerCatalogLoading,
    providerCatalogError,
    refreshProviderCatalog,
    setLlmProvider,
    setLlmModel,
    embeddingCatalog,
    embeddingUpdateLoading,
    embeddingUpdateError,
    applyEmbeddingConfig,
  } = useAppState();

  const providerOptions = providerCatalog.filter((e) => e.enabled);
  const activeProvider  = providerOptions.find((e) => e.provider === llmProvider);
  const activeModels    = activeProvider?.models ?? [];

  const [embeddingBackend,  setEmbeddingBackend]  = useState(embeddingCatalog?.backend   ?? "ollama");
  const [embeddingModelId,  setEmbeddingModelId]  = useState(embeddingCatalog?.model_id  ?? "");
  const [localMessage,      setLocalMessage]      = useState<string | null>(null);
  const [localError,        setLocalError]        = useState<string | null>(null);
  const [refreshing,        setRefreshing]        = useState(false);

  const embeddingModelOptions =
    embeddingBackend === embeddingCatalog?.backend
      ? (embeddingCatalog?.supported_models ?? [])
      : embeddingBackend === "huggingface_local"
        ? HUGGINGFACE_MODEL_OPTIONS
        : OLLAMA_MODEL_OPTIONS;

  useEffect(() => {
    if (!embeddingCatalog) return;
    setEmbeddingBackend(embeddingCatalog.backend);
    setEmbeddingModelId(embeddingCatalog.model_id);
  }, [embeddingCatalog]);

  useEffect(() => {
    const first = embeddingModelOptions[0]?.id ?? embeddingModelId;
    if (!embeddingModelId && first) setEmbeddingModelId(first);
    if (!embeddingModelOptions.some((m) => m.id === embeddingModelId) && first) setEmbeddingModelId(first);
  }, [embeddingBackend, embeddingCatalog, embeddingModelId, embeddingModelOptions]);

  const handleApplyEmbedding = async () => {
    setLocalMessage(null);
    setLocalError(null);
    try {
      await applyEmbeddingConfig(embeddingBackend, embeddingModelId);
      setLocalMessage("Embedding configuration updated successfully.");
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Embedding update failed.");
    }
  };

  const handleRefreshCatalog = async () => {
    setLocalMessage(null);
    setLocalError(null);
    setRefreshing(true);
    try {
      await refreshProviderCatalog();
      setLocalMessage("Provider catalog refreshed.");
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Could not refresh catalog.");
    } finally {
      setRefreshing(false);
    }
  };

  const modelSource      = activeProvider?.source ?? "disabled";
  const modelSourceLabel =
    modelSource === "live"             ? "Live"
    : modelSource === "curated_fallback" ? "Curated fallback"
    : modelSource === "env_fallback"     ? "Env fallback"
    : "Disabled";

  const showCatalogWarning =
    modelSource === "env_fallback" || modelSource === "curated_fallback" || !!providerCatalogError;

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">AI Settings</h1>
        <p className="page-subtitle">Configure the LLM provider, model, and embedding backend used for generation.</p>
      </div>

      {(localError || embeddingUpdateError) && (
        <div className="message error">
          <span>{localError || embeddingUpdateError}</span>
        </div>
      )}
      {localMessage && (
        <div className="message success">
          <CheckCircle2 size={15} />
          <span>{localMessage}</span>
        </div>
      )}

      <div className="settings-grid">

        {/* ── LLM Provider ── */}
        <div className="card">
          <div className="settings-section-label">
            <Cpu size={14} /> LLM Provider
            <span className={`source-badge ${modelSource}`} style={{ marginLeft: "auto" }}>
              {modelSourceLabel}
            </span>
          </div>

          <div className="settings-row">
            <div className="settings-field">
              Provider
              <select
                value={llmProvider}
                onChange={(e) => setLlmProvider(e.target.value as LLMProvider)}
                disabled={providerCatalogLoading || providerOptions.length === 0}
              >
                {providerOptions.length === 0 && <option value={llmProvider}>No providers available</option>}
                {providerOptions.map((entry) => (
                  <option key={entry.provider} value={entry.provider}>{entry.display_name}</option>
                ))}
              </select>
            </div>

            <div className="settings-field">
              Model
              <select
                value={llmModel}
                onChange={(e) => setLlmModel(llmProvider, e.target.value)}
                disabled={providerCatalogLoading || activeModels.length === 0}
              >
                {activeModels.length === 0 && <option value={llmModel || ""}>No models</option>}
                {activeModels.map((m) => (
                  <option key={m.id} value={m.id}>{m.label}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            className="settings-ghost-btn"
            type="button"
            onClick={handleRefreshCatalog}
            disabled={refreshing || providerCatalogLoading}
          >
            <RefreshCw size={13} className={refreshing ? "spin" : ""} />
            {refreshing ? "Refreshing…" : "Refresh model catalog"}
          </button>

          {showCatalogWarning && (
            <p className="settings-warn">
              Live model fetch unavailable — showing fallback list.
              {activeProvider?.source_message ? ` ${activeProvider.source_message}` : ""}
            </p>
          )}
        </div>

        {/* ── Embedding Config ── */}
        <div className="card">
          <div className="settings-section-label">
            <Layers size={14} /> Embedding Backend
            {embeddingCatalog && (
              <span className="embedding-badge" style={{ marginLeft: "auto" }}>
                {embeddingCatalog.backend === "huggingface_local" ? "HF" : "Ollama"} · {embeddingCatalog.dimension}d
              </span>
            )}
          </div>

          {embeddingCatalog && (
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "14px" }}>
              Active: <strong style={{ color: "var(--text-primary)" }}>{embeddingCatalog.model_id}</strong>
            </p>
          )}

          <div className="settings-row">
            <div className="settings-field">
              Backend
              <select
                value={embeddingBackend}
                onChange={(e) => setEmbeddingBackend(e.target.value)}
                disabled={embeddingUpdateLoading}
              >
                {EMBEDDING_BACKEND_OPTIONS.map((b) => (
                  <option key={b.id} value={b.id}>{b.label}</option>
                ))}
              </select>
            </div>

            <div className="settings-field">
              Model
              <select
                value={embeddingModelId}
                onChange={(e) => setEmbeddingModelId(e.target.value)}
                disabled={embeddingUpdateLoading || !embeddingCatalog}
              >
                {embeddingModelOptions.map((m) => (
                  <option key={m.id} value={m.id}>{m.label} ({m.dimension}d)</option>
                ))}
                {!embeddingModelOptions.length && (
                  <option value={embeddingCatalog?.model_id || embeddingModelId}>
                    {embeddingCatalog?.model_id || "No models"}
                  </option>
                )}
              </select>
            </div>
          </div>

          <p className="settings-note">
            Changing embedding model reindexes all future parse jobs. Dimension mismatches will fail
            unless <code>VECTOR_STORE_RESET_ON_MISMATCH=true</code> is set in your environment.
          </p>

          <button
            className="btn btn-primary"
            type="button"
            onClick={handleApplyEmbedding}
            disabled={embeddingUpdateLoading || !embeddingModelId}
            style={{ marginTop: "14px", padding: "9px 18px", fontSize: "0.85rem" }}
          >
            <Layers size={13} />
            {embeddingUpdateLoading ? "Applying…" : "Apply Embedding Config"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsView;