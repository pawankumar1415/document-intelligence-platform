import {
  AlertCircle,
  CheckCircle2,
  DollarSign,
  FileText,
  Loader2,
  ShieldCheck,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useAppState } from "../context/AppStateContext";
import {
  deleteFinancialData,
  deleteRulesDocument,
  getStandardsStatus,
  uploadFinancialData,
  uploadRulesDocument,
} from "../services/api";
import type { StandardsStatus } from "../types/app";

export default function StandardsView() {
  const { token } = useAppState();
  const [status, setStatus] = useState<StandardsStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const [rulesUploading, setRulesUploading] = useState(false);
  const [rulesMsg, setRulesMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const rulesInputRef = useRef<HTMLInputElement>(null);

  const [finUploading, setFinUploading] = useState(false);
  const [finMsg, setFinMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const finInputRef = useRef<HTMLInputElement>(null);

  const load = () => {
    if (!token) return;
    setLoading(true);
    getStandardsStatus({ token })
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [token]);

  /* ── Rules handlers ─────────────────────────────────────────────────────── */

  const handleRulesFile = async (file: File) => {
    if (!token) return;
    setRulesUploading(true);
    setRulesMsg(null);
    try {
      const res = await uploadRulesDocument(file, { token });
      setRulesMsg({ type: "success", text: res.message });
      load();
    } catch (e: unknown) {
      setRulesMsg({ type: "error", text: e instanceof Error ? e.message : "Upload failed." });
    } finally {
      setRulesUploading(false);
      if (rulesInputRef.current) rulesInputRef.current.value = "";
    }
  };

  const handleDeleteRules = async () => {
    if (!token) return;
    await deleteRulesDocument({ token }).catch(() => null);
    setRulesMsg(null);
    load();
  };

  /* ── Financial handlers ─────────────────────────────────────────────────── */

  const handleFinFile = async (file: File) => {
    if (!token) return;
    setFinUploading(true);
    setFinMsg(null);
    try {
      const res = await uploadFinancialData(file, { token });
      setFinMsg({ type: "success", text: res.message });
      load();
    } catch (e: unknown) {
      setFinMsg({ type: "error", text: e instanceof Error ? e.message : "Upload failed." });
    } finally {
      setFinUploading(false);
      if (finInputRef.current) finInputRef.current.value = "";
    }
  };

  const handleDeleteFin = async () => {
    if (!token) return;
    await deleteFinancialData({ token }).catch(() => null);
    setFinMsg(null);
    load();
  };

  /* ── Drag & drop helpers ────────────────────────────────────────────────── */
  const onDrop =
    (handler: (f: File) => void) =>
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      const f = e.dataTransfer.files?.[0];
      if (f) handler(f);
    };

  if (loading) {
    return (
      <div className="view-container">
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-muted)" }}>
          <Loader2 size={16} className="spin" /> Loading standards status…
        </div>
      </div>
    );
  }

  const rules = status?.rules;
  const fin = status?.financial;

  return (
    <div className="view-container">
      <div className="view-header">
        <ShieldCheck size={22} color="var(--bsbi-red)" />
        <div>
          <h1 className="view-title">Standards</h1>
          <p className="view-subtitle">
            Upload your compliance rules and financial reference data. When active, these override default
            scoring behaviour and unlock additional checks.
          </p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>

        {/* ── Rules Document ──────────────────────────────────────────────── */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <FileText size={18} color="var(--bsbi-red)" />
            <h2 style={{ margin: 0, fontSize: "1rem", fontWeight: 700 }}>Compliance Rules</h2>
            {rules?.active ? (
              <span className="badge badge-pass" style={{ marginLeft: "auto" }}>Active</span>
            ) : (
              <span className="badge badge-fail" style={{ marginLeft: "auto" }}>Inactive</span>
            )}
          </div>

          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginBottom: 16 }}>
            Upload a document containing your organisation's narrative standards. The system will extract
            criteria and use them <strong>instead of the default rubric</strong> for all scoring.
            Supported: .docx, .pdf, .xlsx, .csv
          </p>

          {rules?.active && (
            <div className="message success" style={{ marginBottom: 14, fontSize: "0.82rem" }}>
              <CheckCircle2 size={13} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />
              <strong>{rules.rubric_name}</strong> — {rules.criteria_count} criteria active
              {rules.source_filename && (
                <span style={{ color: "var(--text-muted)", marginLeft: 6 }}>({rules.source_filename})</span>
              )}
            </div>
          )}

          <div
            className="dropzone"
            style={{ marginBottom: 12 }}
            onClick={() => rulesInputRef.current?.click()}
            onDrop={onDrop(handleRulesFile)}
            onDragOver={e => e.preventDefault()}
          >
            <input
              ref={rulesInputRef}
              type="file"
              accept=".docx,.pdf,.xlsx,.xls,.csv,.txt"
              style={{ display: "none" }}
              onChange={e => { const f = e.target.files?.[0]; if (f) void handleRulesFile(f); }}
            />
            {rulesUploading ? (
              <><Loader2 size={20} className="spin" /><span>Extracting criteria…</span></>
            ) : (
              <><UploadCloud size={22} /><span>{rules?.active ? "Replace rules document" : "Upload rules document"}</span>
                <span className="dropzone-hint">.docx · .pdf · .xlsx · .csv</span></>
            )}
          </div>

          {rulesMsg && (
            <div className={`message ${rulesMsg.type}`} style={{ fontSize: "0.82rem", marginBottom: 10 }}>
              {rulesMsg.type === "error"
                ? <AlertCircle size={13} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />
                : <CheckCircle2 size={13} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />}
              {rulesMsg.text}
            </div>
          )}

          {rules?.active && (
            <button
              type="button"
              className="btn btn-danger"
              style={{ fontSize: "0.78rem", display: "flex", alignItems: "center", gap: 5 }}
              onClick={() => void handleDeleteRules()}
            >
              <Trash2 size={13} /> Remove rules — revert to default rubric
            </button>
          )}
        </div>

        {/* ── Financial Data ──────────────────────────────────────────────── */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
            <DollarSign size={18} color="var(--bsbi-red)" />
            <h2 style={{ margin: 0, fontSize: "1rem", fontWeight: 700 }}>Financial Reference Data</h2>
            {fin?.active ? (
              <span className="badge badge-pass" style={{ marginLeft: "auto" }}>Layer 3 Active</span>
            ) : (
              <span className="badge" style={{ marginLeft: "auto", background: "var(--bg-subtle)", color: "var(--text-muted)" }}>Layer 3 Off</span>
            )}
          </div>

          <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", marginBottom: 16 }}>
            Upload an Excel or CSV file with monetary/schedule data per project. The{" "}
            <strong>unique ID column must match</strong> the IDs in your narratives. When active, scoring
            adds a financial discrepancy check (Layer 3).
          </p>

          {fin?.active && (
            <div className="message success" style={{ marginBottom: 14, fontSize: "0.82rem" }}>
              <CheckCircle2 size={13} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />
              <strong>{fin.filename}</strong> — {fin.record_count} project records
              {fin.uploaded_at && (
                <span style={{ color: "var(--text-muted)", marginLeft: 6 }}>
                  Uploaded {new Date(fin.uploaded_at).toLocaleDateString()}
                </span>
              )}
            </div>
          )}

          <div
            className="dropzone"
            style={{ marginBottom: 12 }}
            onClick={() => finInputRef.current?.click()}
            onDrop={onDrop(handleFinFile)}
            onDragOver={e => e.preventDefault()}
          >
            <input
              ref={finInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              style={{ display: "none" }}
              onChange={e => { const f = e.target.files?.[0]; if (f) void handleFinFile(f); }}
            />
            {finUploading ? (
              <><Loader2 size={20} className="spin" /><span>Indexing financial data…</span></>
            ) : (
              <><UploadCloud size={22} /><span>{fin?.active ? "Replace financial data" : "Upload financial data"}</span>
                <span className="dropzone-hint">.xlsx · .xls · .csv</span></>
            )}
          </div>

          {finMsg && (
            <div className={`message ${finMsg.type}`} style={{ fontSize: "0.82rem", marginBottom: 10 }}>
              {finMsg.type === "error"
                ? <AlertCircle size={13} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />
                : <CheckCircle2 size={13} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />}
              {finMsg.text}
            </div>
          )}

          {fin?.active && (
            <button
              type="button"
              className="btn btn-danger"
              style={{ fontSize: "0.78rem", display: "flex", alignItems: "center", gap: 5 }}
              onClick={() => void handleDeleteFin()}
            >
              <Trash2 size={13} /> Remove financial data — disable Layer 3
            </button>
          )}
        </div>
      </div>

      {/* ── How it works ────────────────────────────────────────────────────── */}
      <div className="card" style={{ marginTop: 24 }}>
        <h3 style={{ margin: "0 0 12px", fontSize: "0.88rem", fontWeight: 700 }}>How scoring layers work</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          {[
            {
              label: "Layer 1 — Compliance",
              desc: "Scores the narrative against rubric criteria (0–10). Uses your uploaded rules when active, otherwise the default rubric.",
              active: true,
            },
            {
              label: "Layer 2 — Reference Check",
              desc: "Compares the narrative against similar gold-standard examples from your Reference Library to detect abnormalities.",
              active: true,
            },
            {
              label: "Layer 3 — Financial Accuracy",
              desc: "Cross-references monetary and schedule claims in the narrative against your uploaded financial data to flag discrepancies.",
              active: fin?.active ?? false,
            },
          ].map(l => (
            <div
              key={l.label}
              style={{
                padding: "12px 14px",
                borderRadius: 8,
                border: `1px solid ${l.active ? "var(--status-pass)" : "var(--border)"}`,
                background: l.active ? "rgba(34,197,94,0.04)" : "var(--bg-subtle)",
              }}
            >
              <div style={{ fontWeight: 700, fontSize: "0.82rem", marginBottom: 4, display: "flex", alignItems: "center", gap: 6 }}>
                {l.active
                  ? <CheckCircle2 size={13} color="var(--status-pass)" />
                  : <AlertCircle size={13} color="var(--text-muted)" />}
                {l.label}
              </div>
              <p style={{ margin: 0, fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.5 }}>{l.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}