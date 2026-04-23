import { AlertCircle, CheckCircle2, Loader2, Settings } from "lucide-react";
import { useEffect, useState } from "react";
import ModelControlBar from "../components/ModelControlBar";
import { useAppState } from "../context/AppStateContext";
import type { LLMProvider } from "../types/app";

const HUGGINGFACE_MODEL_OPTIONS = [
  { id: "nomic-ai/nomic-embed-text-v1.5",          label: "Nomic Embed Text v1.5",     dimension: 768  },
  { id: "BAAI/bge-m3",                             label: "BGE-M3",                    dimension: 1024 },
  { id: "intfloat/multilingual-e5-large-instruct", label: "Multilingual E5 Large",     dimension: 1024 },
];

const OLLAMA_MODEL_OPTIONS = [
  { id: "qwen3-embedding:0.6b",    label: "qwen3-embedding:0.6b",    dimension: 1024 },
  { id: "mxbai-embed-large:latest", label: "mxbai-embed-large:latest", dimension: 1024 },
  { id: "nomic-embed-text:latest",  label: "nomic-embed-text:latest",  dimension: 768  },
];

export default function SettingsView() {
  const {
    llmProvider, llmModel, setProvider,
    embeddingCatalog, applyEmbeddingConfig,
    refreshProviderCatalog,
  } = useAppState();

  const [provider, setLocalProvider] = useState<LLMProvider>(llmProvider);
  const [model, setModel] = useState<string | null>(llmModel);
  const [embBackend, setEmbBackend] = useState(embeddingCatalog?.backend ?? "huggingface_local");
  const [embModel, setEmbModel] = useState(embeddingCatalog?.model_id ?? "");
  const [saving, setSaving] = useState(false);
  const [embMsg, setEmbMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const embeddingModelOptions =
    embBackend === embeddingCatalog?.backend
      ? (embeddingCatalog?.supported_models ?? [])
      : embBackend === "huggingface_local"
        ? HUGGINGFACE_MODEL_OPTIONS
        : OLLAMA_MODEL_OPTIONS;

  useEffect(() => {
    if (!embeddingCatalog) return;
    setEmbBackend(embeddingCatalog.backend);
    setEmbModel(embeddingCatalog.model_id);
  }, [embeddingCatalog]);

  useEffect(() => {
    const first = embeddingModelOptions[0]?.id ?? embModel;
    if (!embModel && first) { setEmbModel(first); return; }
    if (!embeddingModelOptions.some((m) => m.id === embModel) && first) setEmbModel(first);
  }, [embBackend, embeddingCatalog]);

  const handleProviderChange = (p: LLMProvider, m: string | null) => {
    setLocalProvider(p);
    setModel(m);
    setProvider(p, m);
  };

  const handleSaveEmbedding = async () => {
    setSaving(true);
    setEmbMsg(null);
    try {
      await applyEmbeddingConfig(embBackend, embModel);
      setEmbMsg({ type: "success", text: "Embedding config updated." });
      await refreshProviderCatalog();
    } catch (err) {
      setEmbMsg({ type: "error", text: err instanceof Error ? err.message : "Failed to update." });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title"><Settings size={20} color="var(--bsbi-red)" /> Settings</h1>
        <p className="page-subtitle">Configure AI providers and embedding models.</p>
      </div>

      <div style={{ maxWidth: 560 }}>
        {/* LLM Provider */}
        <div className="settings-section">
          <div className="settings-section-title">LLM Provider</div>
          <div className="card">
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 14 }}>
              Select the AI provider and model used for narrative scoring.
            </p>
            <ModelControlBar provider={provider} model={model} onChange={handleProviderChange} />
          </div>
        </div>

        {/* Embedding model */}
        <div className="settings-section">
          <div className="settings-section-title">Embedding Model</div>
          <div className="card">
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 14 }}>
              Used for indexing reference narratives and retrieving similar examples.
              Changing the model requires re-ingesting all reference files.
            </p>

            <label className="form-label">Backend</label>
            <select
              className="form-control"
              value={embBackend}
              onChange={(e) => setEmbBackend(e.target.value)}
              style={{ marginBottom: 12 }}
            >
              <option value="huggingface_local">HuggingFace Local</option>
              <option value="ollama">Ollama</option>
            </select>

            <label className="form-label">Model</label>
            <select
              className="form-control"
              value={embModel}
              onChange={(e) => setEmbModel(e.target.value)}
              style={{ marginBottom: 14 }}
            >
              {embeddingModelOptions.map((m: { id: string; label: string; dimension: number }) => (
                <option key={m.id} value={m.id}>{m.label} ({m.dimension}d)</option>
              ))}
            </select>

            {embMsg && (
              <div className={`message ${embMsg.type}`} style={{ marginBottom: 12 }}>
                {embMsg.type === "success" ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                {embMsg.text}
              </div>
            )}

            <button
              type="button"
              className="btn btn-primary"
              disabled={saving || !embModel}
              onClick={() => void handleSaveEmbedding()}
            >
              {saving ? <><Loader2 size={14} className="spin" /> Saving…</> : "Save Embedding Config"}
            </button>
          </div>
        </div>

        {/* Current config info */}
        {embeddingCatalog && (
          <div className="settings-section">
            <div className="settings-section-title">Active Configuration</div>
            <div className="card" style={{ fontSize: "0.84rem" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {[
                  ["Backend", embeddingCatalog.backend],
                  ["Model", embeddingCatalog.model_id],
                  ["Dimension", String(embeddingCatalog.dimension)],
                  ["LLM Provider", provider],
                ].map(([label, value]) => (
                  <div key={label}>
                    <div style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginBottom: 2 }}>{label}</div>
                    <div style={{ fontWeight: 600 }}>{value}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}