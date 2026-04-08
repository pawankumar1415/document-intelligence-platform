import {
  AlertCircle,
  CheckCircle2,
  Download,
  Loader2,
  Plus,
  Table2,
  Trash2,
} from "lucide-react";
import { useEffect, useState } from "react";

import { useAppState } from "../context/AppStateContext";
import {
  createExtractionSchema,
  deleteExtractionSchema,
  downloadArtifact,
  extractStructuredData,
  listExtractionSchemas,
} from "../services/api";
import type {
  ExtractionResult,
  ExtractionSchemaField,
  ExtractionSchemaSummary,
} from "../types/app";

const ExtractView = () => {
  const { token, llmProvider, llmModel } = useAppState();

  const [schemas, setSchemas] = useState<ExtractionSchemaSummary[]>([]);
  const [selectedSchemaId, setSelectedSchemaId] = useState<number | null>(null);
  const [docName, setDocName] = useState("");
  const [text, setText] = useState("");
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  // New schema form
  const [showNewSchema, setShowNewSchema] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEntityLabel, setNewEntityLabel] = useState("");
  const [newFields, setNewFields] = useState<ExtractionSchemaField[]>([
    { name: "", description: "", required: true },
  ]);
  const [creatingSchema, setCreatingSchema] = useState(false);

  useEffect(() => {
    listExtractionSchemas({ token }).then((data) => {
      setSchemas(data);
      if (data.length > 0) setSelectedSchemaId(data[0].id);
    }).catch(() => {});
  }, [token]);

  const handleRun = async () => {
    if (!text.trim() || !docName.trim() || !selectedSchemaId) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await extractStructuredData(
        {
          document_name: docName,
          text,
          schema_id: selectedSchemaId,
          llm_provider: llmProvider,
          llm_model: llmModel || null,
        },
        { token },
      );
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extraction failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!result) return;
    setDownloading(true);
    try {
      await downloadArtifact(result.download_url, result.artifact_name, { token });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed.");
    } finally {
      setDownloading(false);
    }
  };

  const handleCreateSchema = async () => {
    if (!newName.trim() || !newEntityLabel.trim()) return;
    const validFields = newFields.filter((f) => f.name.trim());
    setCreatingSchema(true);
    try {
      const created = await createExtractionSchema(
        {
          name: newName.trim(),
          description: "",
          entity_label: newEntityLabel.trim(),
          fields: validFields,
        },
        { token },
      );
      setSchemas((prev) => [...prev, created]);
      setSelectedSchemaId(created.id);
      setShowNewSchema(false);
      setNewName("");
      setNewEntityLabel("");
      setNewFields([{ name: "", description: "", required: true }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create schema.");
    } finally {
      setCreatingSchema(false);
    }
  };

  const handleDeleteSchema = async (schemaId: number) => {
    try {
      await deleteExtractionSchema(schemaId, { token });
      setSchemas((prev) => prev.filter((s) => s.id !== schemaId));
      if (selectedSchemaId === schemaId) setSelectedSchemaId(schemas[0]?.id ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cannot delete built-in schema.");
    }
  };

  const selectedSchema = schemas.find((s) => s.id === selectedSchemaId);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <Table2 size={20} color="var(--bsbi-red)" style={{ marginRight: 8 }} />
          Structured Data Extractor
        </h1>
        <p className="page-subtitle">
          Extract any structured entities from a document into a formatted register. Choose a schema or define your own.
        </p>
      </div>

      <div className="validate-layout">
        {/* ── LEFT: Config ── */}
        <div className="validate-input-col">
          <div className="card">
            <h3 className="card-title">Extraction Schema</h3>

            <label className="form-label">Select schema</label>
            <select
              className="form-control"
              style={{ marginBottom: 8 }}
              value={selectedSchemaId ?? ""}
              onChange={(e) => setSelectedSchemaId(e.target.value ? Number(e.target.value) : null)}
            >
              {schemas.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}{s.is_default ? " (built-in)" : ""}
                </option>
              ))}
            </select>

            {selectedSchema && (
              <div style={{ background: "var(--surface-secondary)", borderRadius: 6, padding: "8px 10px", marginBottom: 10, fontSize: 12, color: "var(--text-muted)" }}>
                Entity: <strong>{selectedSchema.entity_label}</strong>
                {!selectedSchema.is_default && (
                  <button
                    type="button"
                    style={{ float: "right", background: "none", border: "none", cursor: "pointer", color: "var(--status-fail)" }}
                    onClick={() => void handleDeleteSchema(selectedSchema.id)}
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
            )}

            <button
              type="button"
              className="btn btn-secondary"
              style={{ width: "100%", marginBottom: 16 }}
              onClick={() => setShowNewSchema((v) => !v)}
            >
              <Plus size={13} /> {showNewSchema ? "Cancel" : "Create Custom Schema"}
            </button>

            {showNewSchema && (
              <div style={{ border: "1px solid var(--border-color)", borderRadius: 8, padding: 12, marginBottom: 16 }}>
                <label className="form-label">Schema Name</label>
                <input className="form-control" style={{ marginBottom: 8 }} value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="e.g. Budget Items" />
                <label className="form-label">Entity Label (singular)</label>
                <input className="form-control" style={{ marginBottom: 10 }} value={newEntityLabel} onChange={(e) => setNewEntityLabel(e.target.value)} placeholder="e.g. Budget Item" />
                <label className="form-label">Fields</label>
                {newFields.map((f, i) => (
                  <div key={i} style={{ display: "flex", gap: 6, marginBottom: 6 }}>
                    <input
                      className="form-control"
                      placeholder="Field name"
                      value={f.name}
                      onChange={(e) => setNewFields((prev) => prev.map((x, j) => j === i ? { ...x, name: e.target.value } : x))}
                    />
                    <input
                      className="form-control"
                      placeholder="Description (optional)"
                      value={f.description}
                      onChange={(e) => setNewFields((prev) => prev.map((x, j) => j === i ? { ...x, description: e.target.value } : x))}
                    />
                    {newFields.length > 1 && (
                      <button type="button" style={{ background: "none", border: "none", cursor: "pointer", color: "var(--status-fail)" }} onClick={() => setNewFields((prev) => prev.filter((_, j) => j !== i))}>
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                ))}
                <button type="button" className="btn btn-secondary" style={{ width: "100%", marginBottom: 8 }} onClick={() => setNewFields((prev) => [...prev, { name: "", description: "", required: true }])}>
                  <Plus size={13} /> Add Field
                </button>
                <button type="button" className="btn btn-primary" style={{ width: "100%" }} onClick={() => void handleCreateSchema()} disabled={creatingSchema || !newName.trim() || !newEntityLabel.trim()}>
                  {creatingSchema ? <Loader2 size={13} className="spin" /> : <CheckCircle2 size={13} />} Save Schema
                </button>
              </div>
            )}

            <label className="form-label">Document Name</label>
            <input className="form-control" style={{ marginBottom: 10 }} placeholder="e.g. Project Brief" value={docName} onChange={(e) => setDocName(e.target.value)} />

            <label className="form-label">Document Text</label>
            <textarea
              className="form-control validate-textarea"
              rows={10}
              placeholder="Paste the document text to extract from…"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />

            {error && (
              <div className="message error" style={{ marginTop: 10 }}>
                <AlertCircle size={14} /> {error}
              </div>
            )}

            <button
              type="button"
              className="btn btn-primary"
              style={{ width: "100%", marginTop: 12 }}
              onClick={() => void handleRun()}
              disabled={loading || !text.trim() || !docName.trim() || !selectedSchemaId}
            >
              {loading ? <><Loader2 size={14} className="spin" /> Extracting…</> : <><Table2 size={14} /> Run Extraction</>}
            </button>
          </div>
        </div>

        {/* ── RIGHT: Results ── */}
        <div className="validate-results-col">
          {!result && !loading && (
            <div className="validate-empty">
              <Table2 size={40} strokeWidth={1.2} />
              <h2>No results yet</h2>
              <p>Select a schema, paste document text, and click Run Extraction.</p>
            </div>
          )}

          {loading && (
            <div className="validate-empty">
              <Loader2 size={36} className="spin" />
              <h2>Extracting entities…</h2>
              <p>The LLM is scanning the document for {selectedSchema?.entity_label ?? "entities"}.</p>
            </div>
          )}

          {result && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="card validate-verdict-card">
                <div className="validate-verdict-row">
                  <span className="verdict-badge verdict-pass"><CheckCircle2 size={14} /> {result.total_extracted} {result.entity_label} extracted</span>
                </div>
                <div className="validate-verdict-meta">
                  <span>{result.schema_name}</span>
                  <span>·</span>
                  <span>{result.field_names.length} fields</span>
                </div>
              </div>

              {result.rows.length > 0 ? (
                <div className="card" style={{ overflowX: "auto" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <h3 className="card-title" style={{ margin: 0 }}>Extracted {result.entity_label} Entries</h3>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ fontSize: 12 }}
                      onClick={() => void handleDownload()}
                      disabled={downloading}
                    >
                      {downloading ? <Loader2 size={13} className="spin" /> : <Download size={13} />} Download Register
                    </button>
                  </div>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                    <thead>
                      <tr style={{ background: "#B11223" }}>
                        {result.field_names.map((col, i) => (
                          <th key={i} style={{ padding: "7px 10px", textAlign: "left", color: "white", fontWeight: 600, whiteSpace: "nowrap" }}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.map((row, ri) => (
                        <tr key={ri} style={{ background: ri % 2 === 0 ? "#f5f5f5" : "white" }}>
                          {row.map((cell, ci) => (
                            <td key={ci} style={{ padding: "7px 10px", borderBottom: "1px solid var(--border-color)", verticalAlign: "top" }}>{cell || <span style={{ color: "var(--text-muted)" }}>—</span>}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="card">
                  <p style={{ color: "var(--text-muted)", fontSize: 14 }}>No {result.entity_label} entities were found in the document.</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ExtractView;