import { useEffect } from "react";
import { useAppState } from "../context/AppStateContext";
import type { LLMProvider } from "../types/app";

interface Props {
  provider: LLMProvider;
  model: string | null;
  onChange: (provider: LLMProvider, model: string | null) => void;
}

export default function ModelControlBar({ provider, model, onChange }: Props) {
  const { providerCatalog } = useAppState();
  const providers = providerCatalog?.providers?.filter((p) => p.enabled) ?? [];
  const currentProvider = providers.find((p) => p.provider === provider);
  const models = currentProvider?.models ?? [];

  // Auto-correct stale model selection (e.g. a model that no longer exists in catalog)
  useEffect(() => {
    if (models.length === 0 || model === null) return;
    if (!models.some((m) => m.id === model)) {
      const fallback = currentProvider?.default_model ?? models[0]?.id ?? null;
      if (fallback !== model) onChange(provider, fallback);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [models.map((m) => m.id).join(","), model]);

  return (
    <div className="model-bar">
      <span className="model-bar-label">LLM:</span>
      <select
        value={provider}
        onChange={(e) => {
          const newProvider = e.target.value as LLMProvider;
          const newDefault = providers.find((p) => p.provider === newProvider)?.default_model ?? null;
          onChange(newProvider, newDefault);
        }}
      >
        {providers.map((p) => (
          <option key={p.provider} value={p.provider}>{p.display_name}</option>
        ))}
        {providers.length === 0 && <option value={provider}>{provider}</option>}
      </select>

      {models.length > 0 && (
        <select
          value={model ?? currentProvider?.default_model ?? ""}
          onChange={(e) => onChange(provider, e.target.value)}
        >
          {models.map((m) => (
            <option key={m.id} value={m.id}>{m.label}</option>
          ))}
        </select>
      )}
    </div>
  );
}