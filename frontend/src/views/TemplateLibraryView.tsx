import { AlertCircle, BookMarked, ChevronDown, Plus, Star, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";

import { useAppState } from "../context/AppStateContext";
import { createTemplate, deleteTemplate, listTemplates } from "../services/api";
import type { GenerationTemplateSummary, TemplateType } from "../types/app";

const TYPE_LABELS: Record<TemplateType, string> = {
  sow: "Statement of Work",
  pptx: "PowerPoint Deck",
  bid: "Bid Response",
  case_study: "Case Study",
};

const TYPE_OPTIONS: TemplateType[] = ["sow", "pptx", "bid", "case_study"];

const TemplateLibraryView = () => {
  const { token } = useAppState();

  const [templates, setTemplates] = useState<GenerationTemplateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<TemplateType | "">("");
  const [showCreate, setShowCreate] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);

  // New template form state
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newType, setNewType] = useState<TemplateType>("sow");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadTemplates();
  }, [filterType]);

  const loadTemplates = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listTemplates({
        token,
        templateType: filterType || null,
      });
      setTemplates(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load templates.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const tpl = await createTemplate(
        { name: newName.trim(), description: newDesc.trim(), template_type: newType, config: {} },
        { token },
      );
      setTemplates((prev) => [
        { ...tpl, is_default: false },
        ...prev.filter((t) => !filterType || t.template_type === filterType),
      ]);
      setNewName("");
      setNewDesc("");
      setShowCreate(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create template.");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: number) => {
    setDeleting(id);
    setError(null);
    try {
      await deleteTemplate(id, { token });
      setTemplates((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete template.");
    } finally {
      setDeleting(null);
    }
  };

  const fmtDate = (iso: string) =>
    new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });

  const grouped = TYPE_OPTIONS.reduce<Record<TemplateType, GenerationTemplateSummary[]>>(
    (acc, t) => {
      acc[t] = templates.filter((tpl) => tpl.template_type === t);
      return acc;
    },
    { sow: [], pptx: [], bid: [], case_study: [] },
  );

  const displayTypes = filterType ? [filterType] : TYPE_OPTIONS;

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <h1 className="page-title">Template Library</h1>
          <p className="page-subtitle">
            Saved generation presets — default templates are provided per document type. Create custom ones for recurring engagements.
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
          {/* Filter */}
          <div style={{ position: "relative" }}>
            <select
              className="form-input"
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as TemplateType | "")}
              style={{ paddingRight: "28px", appearance: "none", fontSize: "0.85rem" }}
            >
              <option value="">All types</option>
              {TYPE_OPTIONS.map((t) => (
                <option key={t} value={t}>{TYPE_LABELS[t]}</option>
              ))}
            </select>
            <ChevronDown size={13} style={{ position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)", pointerEvents: "none", color: "var(--text-muted)" }} />
          </div>

          <button
            className="btn btn-primary"
            type="button"
            onClick={() => setShowCreate((v) => !v)}
          >
            {showCreate ? <X size={14} /> : <Plus size={14} />}
            {showCreate ? "Cancel" : "New Template"}
          </button>
        </div>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="card" style={{ marginBottom: "24px", padding: "20px" }}>
          <h3 style={{ margin: "0 0 14px", fontSize: "0.95rem", fontWeight: 600 }}>New Template</h3>
          <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ display: "flex", gap: "10px" }}>
              <input
                className="form-input"
                type="text"
                placeholder="Template name…"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                style={{ flex: 1 }}
                autoFocus
              />
              <div style={{ position: "relative" }}>
                <select
                  className="form-input"
                  value={newType}
                  onChange={(e) => setNewType(e.target.value as TemplateType)}
                  style={{ paddingRight: "28px", appearance: "none" }}
                >
                  {TYPE_OPTIONS.map((t) => (
                    <option key={t} value={t}>{TYPE_LABELS[t]}</option>
                  ))}
                </select>
                <ChevronDown size={13} style={{ position: "absolute", right: "8px", top: "50%", transform: "translateY(-50%)", pointerEvents: "none", color: "var(--text-muted)" }} />
              </div>
            </div>
            <input
              className="form-input"
              type="text"
              placeholder="Description (optional)…"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
            />
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button className="btn btn-primary" type="submit" disabled={creating || !newName.trim()}>
                {creating ? "Creating…" : "Create Template"}
              </button>
            </div>
          </form>
        </div>
      )}

      {error && (
        <div className="message error" style={{ marginBottom: "16px" }}>
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="card" style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Loading templates…
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
          {displayTypes.map((type) => (
            <section key={type}>
              <h2 style={{ fontSize: "0.92rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "10px" }}>
                {TYPE_LABELS[type]}
              </h2>

              {grouped[type].length === 0 ? (
                <div className="card" style={{ padding: "20px", color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center" }}>
                  No templates for {TYPE_LABELS[type]}.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {grouped[type].map((tpl) => (
                    <div
                      key={tpl.id}
                      className="card"
                      style={{ padding: "14px 18px", display: "flex", alignItems: "center", gap: "12px" }}
                    >
                      <div style={{ color: tpl.is_default ? "var(--bsbi-red)" : "var(--text-muted)", flexShrink: 0 }}>
                        {tpl.is_default ? <Star size={16} fill="currentColor" /> : <BookMarked size={16} />}
                      </div>

                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 600, fontSize: "0.9rem", display: "flex", alignItems: "center", gap: "8px" }}>
                          {tpl.name}
                          {tpl.is_default && (
                            <span style={{
                              fontSize: "0.68rem", fontWeight: 700, color: "var(--bsbi-red)",
                              background: "rgba(177,18,35,0.08)", border: "1px solid rgba(177,18,35,0.2)",
                              borderRadius: "10px", padding: "1px 7px", textTransform: "uppercase", letterSpacing: "0.04em",
                            }}>
                              Default
                            </span>
                          )}
                        </div>
                        {tpl.description && (
                          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "2px" }}>
                            {tpl.description}
                          </div>
                        )}
                      </div>

                      <div style={{ fontSize: "0.77rem", color: "var(--text-muted)", flexShrink: 0 }}>
                        {fmtDate(tpl.created_at)}
                      </div>

                      {!tpl.is_default && (
                        <button
                          className="btn btn-secondary"
                          type="button"
                          onClick={() => handleDelete(tpl.id)}
                          disabled={deleting === tpl.id}
                          style={{ padding: "5px 10px", flexShrink: 0 }}
                          title="Delete template"
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  );
};

export default TemplateLibraryView;