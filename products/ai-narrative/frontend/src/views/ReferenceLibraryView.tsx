import { AlertCircle, BookOpen, CheckCircle2, FileSpreadsheet, Info, Loader2, Trash2, UploadCloud } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useAppState } from "../context/AppStateContext";
import { deleteReference, ingestReference, listReferences } from "../services/api";
import type { ReferenceFileRecord } from "../types/app";

const DEFAULT_CRITERIA = [
  { name: "Clarity",           severity: "HIGH",   desc: "Writing is clear and unambiguous — no vague or confusing language." },
  { name: "Completeness",      severity: "HIGH",   desc: "All required information is present with no unexplained gaps." },
  { name: "Accuracy",          severity: "HIGH",   desc: "Figures, dates, and claims are correct and consistent with supporting data." },
  { name: "Structure",         severity: "MEDIUM", desc: "Content flows logically with a clear beginning, context, and outcome." },
  { name: "Professional Tone", severity: "MEDIUM", desc: "Language is formal and appropriate for a professional report." },
  { name: "No Jargon",         severity: "LOW",    desc: "Acronyms are expanded on first use; technical terms are explained." },
  { name: "Consistent Dates",  severity: "LOW",    desc: "Date formats are consistent throughout the narrative." },
];

const severityColour: Record<string, string> = {
  HIGH: "var(--status-fail)",
  MEDIUM: "var(--status-warn)",
  LOW: "var(--status-pass)",
};

export default function ReferenceLibraryView() {
  const { token, rubrics } = useAppState();
  const [files, setFiles] = useState<ReferenceFileRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadFiles = async () => {
    setLoading(true);
    try {
      const data = await listReferences({ token });
      setFiles(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reference files.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadFiles(); }, [token]);

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await ingestReference(selectedFile, { token, description });
      setSuccess(`${result.message} (${result.record_count} records indexed)`);
      setSelectedFile(null);
      setDescription("");
      void loadFiles();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (fileId: number, filename: string) => {
    if (!confirm(`Delete reference file "${filename}"? This will remove its embeddings from the vector store.`)) return;
    try {
      await deleteReference(fileId, { token });
      setFiles((prev) => prev.filter((f) => f.id !== fileId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title"><BookOpen size={20} color="var(--bsbi-red)" /> Reference Library</h1>
        <p className="page-subtitle">
          Upload reference Excel/CSV files containing "gold standard" narratives.
          These are embedded and used for abnormality detection during scoring.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 20, alignItems: "start" }}>
        {/* Upload card */}
        <div className="card">
          <h3 className="card-title">Upload Reference File</h3>
          <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: 14 }}>
            Accepted formats: .xlsx, .xls, .csv<br />
            Required columns: unique ID + narrative text
          </p>

          <div
            className={`dropzone${selectedFile ? " dropzone-loaded" : ""}`}
            style={{ marginBottom: 14 }}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              style={{ display: "none" }}
              onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
            />
            {selectedFile ? (
              <>
                <FileSpreadsheet size={20} color="var(--bsbi-red)" />
                <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>{selectedFile.name}</span>
                <span className="dropzone-hint">Click to change</span>
              </>
            ) : (
              <>
                <UploadCloud size={24} />
                <span>Click to select file</span>
                <span className="dropzone-hint">.xlsx · .xls · .csv</span>
              </>
            )}
          </div>

          <label className="form-label">Description (optional)</label>
          <input
            className="form-control"
            placeholder="e.g. NDA P07 reference narratives"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            style={{ marginBottom: 14 }}
          />

          {error && <div className="message error" style={{ marginBottom: 12 }}><AlertCircle size={14} /> {error}</div>}
          {success && <div className="message success" style={{ marginBottom: 12 }}><CheckCircle2 size={14} /> {success}</div>}

          <button
            type="button"
            className="btn btn-primary"
            style={{ width: "100%", justifyContent: "center" }}
            disabled={uploading || !selectedFile}
            onClick={() => void handleUpload()}
          >
            {uploading ? <><Loader2 size={14} className="spin" /> Indexing…</> : <><UploadCloud size={14} /> Index Reference File</>}
          </button>
        </div>

        {/* Files list */}
        <div>
          <h3 className="card-title">Indexed Reference Files</h3>
          {loading && <div style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>Loading…</div>}
          {!loading && files.length === 0 && (
            <div>
              <div className="message" style={{ marginBottom: 16, fontSize: "0.85rem", background: "var(--bg-tertiary)", border: "1px solid var(--border-color)", borderRadius: 8, padding: "12px 14px", display: "flex", gap: 10, alignItems: "flex-start" }}>
                <Info size={15} style={{ flexShrink: 0, marginTop: 1, color: "var(--text-muted)" }} />
                <span>
                  <strong>No reference files yet.</strong> Layer 1 (rubric compliance) still works without references.
                  Layer 2 (abnormality detection) will be skipped until you upload at least one file.
                </span>
              </div>

              <div className="card">
                <h4 className="card-title" style={{ marginBottom: 10 }}>
                  Default Rubric Criteria
                  {rubrics.find(r => r.is_default) && (
                    <span style={{ fontWeight: 400, color: "var(--text-muted)", fontSize: "0.78rem", marginLeft: 8 }}>
                      — {rubrics.find(r => r.is_default)?.name}
                    </span>
                  )}
                </h4>
                <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginBottom: 12 }}>
                  Every narrative is checked against these criteria even without reference files.
                  Upload narratives that already <em>pass</em> these as your gold-standard examples.
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {DEFAULT_CRITERIA.map((c) => (
                    <div key={c.name} style={{ display: "flex", alignItems: "flex-start", gap: 10, fontSize: "0.84rem" }}>
                      <span style={{ fontSize: "0.7rem", fontWeight: 700, color: severityColour[c.severity], background: `${severityColour[c.severity]}18`, border: `1px solid ${severityColour[c.severity]}40`, borderRadius: 4, padding: "1px 6px", whiteSpace: "nowrap", marginTop: 1 }}>
                        {c.severity}
                      </span>
                      <span><strong>{c.name}</strong> — {c.desc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          <div className="ref-grid">
            {files.map((f) => (
              <div className="ref-card" key={f.id}>
                <FileSpreadsheet size={18} color="var(--bsbi-red)" style={{ flexShrink: 0 }} />
                <div className="ref-card-info">
                  <div className="ref-card-name">{f.filename}</div>
                  <div className="ref-card-meta">
                    {f.description && <span>{f.description} · </span>}
                    Indexed {new Date(f.indexed_at).toLocaleDateString()}
                  </div>
                </div>
                <span className="ref-card-badge">{f.record_count} records</span>
                <button
                  type="button"
                  className="btn btn-danger"
                  style={{ padding: "6px 10px" }}
                  onClick={() => void handleDelete(f.id, f.filename)}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}