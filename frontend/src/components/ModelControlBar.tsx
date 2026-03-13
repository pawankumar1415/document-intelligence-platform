import { Cpu, Layers } from "lucide-react";
import { useEffect, useState } from "react";

import { useAppState } from "../context/AppStateContext";
import type { LLMProvider } from "../types/app";

const EMBEDDING_BACKEND_OPTIONS = [
  { id: "ollama", label: "Ollama" },
  { id: "huggingface_local", label: "Hugging Face Local" },
];

const HUGGINGFACE_MODEL_OPTIONS = [
  { id: "nomic-ai/nomic-embed-text-v1.5", label: "Nomic Embed Text v1.5", dimension: 768 },
  { id: "BAAI/bge-m3", label: "BGE-M3", dimension: 1024 },
  { id: "intfloat/multilingual-e5-large-instruct", label: "Multilingual E5 Large Instruct", dimension: 1024 },
];

const OLLAMA_MODEL_OPTIONS = [
  { id: "qwen3-embedding:4b", label: "qwen3-embedding:4b", dimension: 2560 },
  { id: "qwen3-embedding:0.6b", label: "qwen3-embedding:0.6b", dimension: 1024 },
  { id: "nomic-embed-text", label: "nomic-embed-text", dimension: 768 },
  { id: "mxbai-embed-large", label: "mxbai-embed-large", dimension: 1024 },
  { id: "bge-m3", label: "bge-m3", dimension: 1024 },
  { id: "all-minilm", label: "all-minilm", dimension: 384 },
];

const ModelControlBar = () => {
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

  const providerOptions = providerCatalog.filter((entry) => entry.enabled);
  const activeProvider = providerOptions.find((entry) => entry.provider === llmProvider);
  const activeModels = activeProvider?.models ?? [];

  const [embeddingBackend, setEmbeddingBackend] = useState(embeddingCatalog?.backend ?? "ollama");
  const [embeddingModelId, setEmbeddingModelId] = useState(embeddingCatalog?.model_id ?? "");
  const [localMessage, setLocalMessage] = useState<string | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [showEmbeddingSettings, setShowEmbeddingSettings] = useState(false);
  const embeddingModelOptions =
    embeddingBackend === embeddingCatalog?.backend
      ? embeddingCatalog?.supported_models ?? []
      : embeddingBackend === "huggingface_local"
        ? HUGGINGFACE_MODEL_OPTIONS
        : OLLAMA_MODEL_OPTIONS;

  useEffect(() => {
    if (!embeddingCatalog) {
      return;
    }
    setEmbeddingBackend(embeddingCatalog.backend);
    setEmbeddingModelId(embeddingCatalog.model_id);
  }, [embeddingCatalog]);

  useEffect(() => {
    const firstModel = embeddingModelOptions[0]?.id ?? embeddingModelId;
    if (!embeddingModelId && firstModel) {
      setEmbeddingModelId(firstModel);
    }
    if (!embeddingModelOptions.some((model) => model.id === embeddingModelId) && firstModel) {
      setEmbeddingModelId(firstModel);
    }
  }, [embeddingBackend, embeddingCatalog, embeddingModelId, embeddingModelOptions]);

  const handleApply = async () => {
    setLocalMessage(null);
    setLocalError(null);
    try {
      await applyEmbeddingConfig(embeddingBackend, embeddingModelId);
      setLocalMessage("Embedding configuration updated.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Embedding update failed.";
      setLocalError(message);
    }
  };
  const handleRefreshModels = async () => {
    setLocalMessage(null);
    setLocalError(null);
    try {
      await refreshProviderCatalog();
      setLocalMessage("Provider model catalog refreshed.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not refresh provider catalog.";
      setLocalError(message);
    }
  };

  const modelSource = activeProvider?.source ?? "disabled";
  const modelSourceMessage = activeProvider?.source_message;
  const modelSourceLabel =
    modelSource === "live"
      ? "Live"
      : modelSource === "curated_fallback"
        ? "Curated fallback"
        : modelSource === "env_fallback"
          ? "Fallback"
          : modelSource;

  return (
    <section className="model-control-bar panel">
      <div className="model-control-heading">
        <h3>
          <Cpu size={16} /> AI Runtime Controls
        </h3>
        <p>Choose generation provider/model and optional embedding settings for new parse operations.</p>
      </div>

      <div className="model-control-grid compact">
        <label>
          LLM Provider
          <select
            className="provider-select"
            value={llmProvider}
            onChange={(event) => setLlmProvider(event.target.value as LLMProvider)}
            disabled={providerCatalogLoading || providerOptions.length === 0}
          >
            {providerOptions.length === 0 && <option value={llmProvider}>No providers</option>}
            {providerOptions.map((entry) => (
              <option key={entry.provider} value={entry.provider}>
                {entry.display_name}
              </option>
            ))}
          </select>
        </label>

        <label>
          LLM Model
          <select
            className="provider-select"
            value={llmModel}
            onChange={(event) => setLlmModel(llmProvider, event.target.value)}
            disabled={providerCatalogLoading || activeModels.length === 0}
          >
            {activeModels.length === 0 && <option value={llmModel || ""}>No models</option>}
            {activeModels.map((model) => (
              <option key={model.id} value={model.id}>
                {model.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="model-control-actions">
        <button
          className="btn-ghost"
          type="button"
          onClick={handleRefreshModels}
          disabled={providerCatalogLoading}
        >
          Refresh Models
        </button>
        <button className="btn-ghost" type="button" onClick={() => setShowEmbeddingSettings((current) => !current)}>
          {showEmbeddingSettings ? "Hide Embedding Settings" : "Show Embedding Settings"}
        </button>
        <span className={`provider-source ${modelSource}`}>
          Provider catalog: {modelSourceLabel}
        </span>
      </div>

      {showEmbeddingSettings && (
        <div className="model-control-grid">
          <label>
            Embedding Backend
            <select
              className="provider-select"
              value={embeddingBackend}
              onChange={(event) => setEmbeddingBackend(event.target.value)}
              disabled={embeddingUpdateLoading}
            >
              {EMBEDDING_BACKEND_OPTIONS.map((backend) => (
                <option key={backend.id} value={backend.id}>
                  {backend.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            Embedding Model
            <select
              className="provider-select"
              value={embeddingModelId}
              onChange={(event) => setEmbeddingModelId(event.target.value)}
              disabled={embeddingUpdateLoading || !embeddingCatalog}
            >
              {embeddingModelOptions.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.label} ({model.dimension})
                </option>
              ))}
              {!embeddingModelOptions.length && (
                <option value={embeddingCatalog?.model_id || embeddingModelId}>
                  {embeddingCatalog?.model_id || "No embedding models"}
                </option>
              )}
            </select>
          </label>
          <div className="model-control-inline-action">
            <button
              className="btn-primary"
              type="button"
              onClick={handleApply}
              disabled={embeddingUpdateLoading || !embeddingModelId}
            >
              <Layers size={14} /> {embeddingUpdateLoading ? "Applying..." : "Apply Embedding"}
            </button>
          </div>
        </div>
      )}

      <div className="model-control-actions">
        <button
          className="btn-ghost"
          type="button"
          onClick={() => setShowEmbeddingSettings(true)}
          disabled={showEmbeddingSettings}
        >
          Configure Embeddings
        </button>
        <span className="model-control-note">
          Active: {embeddingCatalog?.backend || "-"} / {embeddingCatalog?.model_id || "-"} / dim{" "}
          {embeddingCatalog?.dimension ?? "-"}
        </span>
      </div>
      <p className="model-control-note">
        Switching embedding backend/model affects new parse jobs and can fail if pgvector dimension mismatches
        existing data.
      </p>
      {(activeProvider?.source === "env_fallback" ||
        activeProvider?.source === "curated_fallback" ||
        providerCatalogError) && (
        <div className="message error">
          <span>
            Live model fetch is unavailable for this provider right now. Showing fallback model list.
            {modelSourceMessage ? ` Details: ${modelSourceMessage}` : ""}
            {providerCatalogError ? ` ${providerCatalogError}` : ""}
          </span>
        </div>
      )}

      {(localError || embeddingUpdateError) && (
        <div className="message error">
          <span>{localError || embeddingUpdateError}</span>
        </div>
      )}
      {localMessage && (
        <div className="message success">
          <span>{localMessage}</span>
        </div>
      )}
    </section>
  );
};

export default ModelControlBar;
