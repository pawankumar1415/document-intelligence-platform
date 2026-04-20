import {
  AlertCircle,
  ArrowUpDown,
  CheckCircle2,
  FileText,
  Loader2,
  TrendingDown,
  TrendingUp,
  Minus,
} from "lucide-react";
import { useState } from "react";

import { useAppState } from "../context/AppStateContext";
import { compareDocuments } from "../services/api";
import type { ComparisonChange, ComparisonResult } from "../types/app";

const SentimentIcon = ({ sentiment }: { sentiment: string }) => {
  if (sentiment === "improved") return <TrendingUp size={18} color="var(--status-pass)" />;
  if (sentiment === "regressed") return <TrendingDown size={18} color="var(--status-fail)" />;
  return <Minus size={18} color="var(--text-muted)" />;
};

const ChangeTypeBadge = ({ type }: { type: ComparisonChange["change_type"] }) => {
  const map: Record<string, { label: string; cls: string }> = {
    improved: { label: "Improved", cls: "verdict-pass" },
    regressed: { label: "Regressed", cls: "verdict-fail" },
    added: { label: "Added", cls: "verdict-pass" },
    removed: { label: "Removed", cls: "verdict-fail" },
    unchanged: { label: "Unchanged", cls: "" },
  };
  const { label, cls } = map[type] ?? { label: type, cls: "" };
  return <span className={`verdict-badge ${cls}`} style={{ fontSize: 11 }}>{label}</span>;
};

const ScoreBar = ({ score, label }: { score: number; label: string }) => {
  const color = score >= 7 ? "var(--status-pass)" : score >= 5 ? "var(--status-warn)" : "var(--status-fail)";
  return (
    <div style={{ flex: 1 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{label}</span>
        <span style={{ fontSize: 13, fontWeight: 600, color }}>{score.toFixed(1)}/10</span>
      </div>
      <div style={{ height: 6, background: "var(--border-color)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${score * 10}%`, height: "100%", background: color, borderRadius: 3 }} />
      </div>
    </div>
  );
};

const CompareView = () => {
  const { token, llmProvider, llmModel } = useAppState();

  const [docAName, setDocAName] = useState("");
  const [docAText, setDocAText] = useState("");
  const [docBName, setDocBName] = useState("");
  const [docBText, setDocBText] = useState("");
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = (side: "a" | "b") => (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      if (side === "a") { setDocAText(text); if (!docAName) setDocAName(file.name.replace(/\.[^.]+$/, "")); }
      else { setDocBText(text); if (!docBName) setDocBName(file.name.replace(/\.[^.]+$/, "")); }
    };
    reader.readAsText(file);
  };

  const handleRun = async () => {
    if (!docAText.trim() || !docBText.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await compareDocuments(
        {
          doc_a_name: docAName || "Document A",
          doc_a_text: docAText,
          doc_b_name: docBName || "Document B",
          doc_b_text: docBText,
          llm_provider: llmProvider,
          llm_model: llmModel || null,
        },
        { token },
      );
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comparison failed.");
    } finally {
      setLoading(false);
    }
  };

  const canRun = docAText.trim().length > 0 && docBText.trim().length > 0;

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <ArrowUpDown size={20} color="var(--bsbi-red)" style={{ marginRight: 8 }} />
          Document Comparison
        </h1>
        <p className="page-subtitle">
          Compare two document versions to identify improvements, regressions, and structural changes.
        </p>
      </div>

      {/* ── Input panels ── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        {(["a", "b"] as const).map((side) => {
          const name = side === "a" ? docAName : docBName;
          const text = side === "a" ? docAText : docBText;
          const setName = side === "a" ? setDocAName : setDocBName;
          const setText = side === "a" ? setDocAText : setDocBText;
          const label = side === "a" ? "Document A (Original / Baseline)" : "Document B (Revised / New Version)";
          return (
            <div className="card" key={side}>
              <h3 className="card-title" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <FileText size={15} color="var(--bsbi-red)" /> {label}
              </h3>
              <label className="form-label">Name</label>
              <input
                className="form-control"
                style={{ marginBottom: 10 }}
                placeholder={`e.g. SOW v${side === "a" ? "1" : "2"}`}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <label className="form-label">
                Text
                <label style={{ marginLeft: 8, cursor: "pointer", color: "var(--bsbi-red)", fontSize: 12 }}>
                  ↑ Upload file
                  <input type="file" accept=".txt,.md" style={{ display: "none" }} onChange={handleFileUpload(side)} />
                </label>
              </label>
              <textarea
                className="form-control"
                rows={10}
                placeholder="Paste document text or upload a .txt file…"
                value={text}
                onChange={(e) => setText(e.target.value)}
                style={{ resize: "vertical" }}
              />
            </div>
          );
        })}
      </div>

      {error && (
        <div className="message error" style={{ marginBottom: 12 }}>
          <AlertCircle size={14} /> {error}
        </div>
      )}

      <button
        type="button"
        className="btn btn-primary"
        style={{ marginBottom: 24, minWidth: 200 }}
        onClick={() => void handleRun()}
        disabled={loading || !canRun}
      >
        {loading ? <><Loader2 size={14} className="spin" /> Comparing…</> : <><ArrowUpDown size={14} /> Compare Documents</>}
      </button>

      {/* ── Results ── */}
      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Summary card */}
          <div className="card">
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <SentimentIcon sentiment={result.overall_sentiment} />
              <h3 className="card-title" style={{ margin: 0 }}>
                {result.overall_sentiment === "improved" ? "Overall: Improved" :
                 result.overall_sentiment === "regressed" ? "Overall: Regressed" : "Overall: Neutral"}
              </h3>
            </div>
            <p style={{ color: "var(--text-muted)", fontSize: 14, marginBottom: 16 }}>{result.summary}</p>
            <div style={{ display: "flex", gap: 16 }}>
              <ScoreBar score={result.doc_a_score} label={result.doc_a_name || "Doc A"} />
              <ScoreBar score={result.doc_b_score} label={result.doc_b_name || "Doc B"} />
            </div>
          </div>

          {/* Improvements & Regressions */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {result.key_improvements.length > 0 && (
              <div className="card validate-issues-card validate-issues-pass">
                <h4 className="validate-issues-title"><CheckCircle2 size={14} /> Key Improvements in Doc B</h4>
                <ul className="validate-issues-list">
                  {result.key_improvements.map((item, i) => <li key={i}>{item}</li>)}
                </ul>
              </div>
            )}
            {result.key_regressions.length > 0 && (
              <div className="card validate-issues-card validate-issues-fail">
                <h4 className="validate-issues-title"><AlertCircle size={14} /> Regressions vs Doc A</h4>
                <ul className="validate-issues-list">
                  {result.key_regressions.map((item, i) => <li key={i}>{item}</li>)}
                </ul>
              </div>
            )}
          </div>

          {/* Change table */}
          {result.changes.length > 0 && (
            <div className="card">
              <h3 className="card-title">Detailed Changes</h3>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid var(--border-color)" }}>
                    <th style={{ textAlign: "left", padding: "6px 8px", color: "var(--text-muted)" }}>Section</th>
                    <th style={{ textAlign: "left", padding: "6px 8px", color: "var(--text-muted)" }}>Change</th>
                    <th style={{ textAlign: "left", padding: "6px 8px", color: "var(--text-muted)" }}>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {result.changes.map((change, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid var(--border-color)" }}>
                      <td style={{ padding: "8px", fontWeight: 500 }}>{change.section}</td>
                      <td style={{ padding: "8px" }}><ChangeTypeBadge type={change.change_type} /></td>
                      <td style={{ padding: "8px", color: "var(--text-muted)" }}>{change.details}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {!result && !loading && (
        <div className="validate-empty">
          <ArrowUpDown size={40} strokeWidth={1.2} />
          <h2>No comparison yet</h2>
          <p>Paste two documents above and click Compare to see what has changed.</p>
        </div>
      )}
    </div>
  );
};

export default CompareView;