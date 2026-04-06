import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  FileText,
  Loader2,
  RefreshCw,
  UploadCloud,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import SharePointPicker from "../components/SharePointPicker";
import { useAppState } from "../context/AppStateContext";
import { listRubrics, sharePointDownloadAndParse, validateDocument } from "../services/api";
import type { RubricSummary, SharePointFile, ValidationResult } from "../types/app";

type Source = "manual" | "sharepoint";

const VerdictBadge = ({ verdict }: { verdict: string }) => {
  if (verdict === "PASS")
    return <span className="verdict-badge verdict-pass"><CheckCircle2 size={14} /> PASS</span>;
  if (verdict === "PASS_WITH_WARNINGS")
    return <span className="verdict-badge verdict-warn"><AlertCircle size={14} /> PASS WITH WARNINGS</span>;
  return <span className="verdict-badge verdict-fail"><XCircle size={14} /> FAIL</span>;
};

const ScoreRing = ({ score }: { score: number }) => {
  const colour = score >= 8 ? "var(--status-pass)" : score >= 6 ? "var(--status-warn)" : "var(--status-fail)";
  return (
    <div className="score-ring" style={{ "--ring-colour": colour } as React.CSSProperties}>
      <span className="score-ring-value">{score.toFixed(1)}</span>
      <span className="score-ring-label">/ 10</span>
    </div>
  );
};

const DiffText = ({ original, rewritten }: { original: string; rewritten: string }) => {
  if (!rewritten) return null;
  // Simple word-level diff highlight — green for added, red for removed
  const origWords = original.split(/\s+/);
  const rewriteWords = rewritten.split(/\s+/);
  const added = new Set(rewriteWords.filter((w) => !origWords.includes(w)));
  const removed = new Set(origWords.filter((w) => !rewriteWords.includes(w)));
  return (
    <p className="diff-text">
      {rewriteWords.map((word, i) => {
        const cls = added.has(word) ? "diff-add" : removed.has(word) ? "diff-remove" : "";
        return (
          <span key={i} className={cls}>
            {word}{" "}
          </span>
        );
      })}
    </p>
  );
};

const ValidateView = () => {
  const { token, llmProvider, llmModel, parsedDocument } = useAppState();

  const [source, setSource] = useState<Source>("manual");
  const [docName, setDocName] = useState("");
  const [text, setText] = useState("");
  const [rubrics, setRubrics] = useState<RubricSummary[]>([]);
  const [selectedRubricId, setSelectedRubricId] = useState<number | null>(null);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRewrite, setShowRewrite] = useState(false);
  const [appliedRewrite, setAppliedRewrite] = useState(false);
  const [spLoading, setSpLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Pre-fill from parsed document in Studio if available
  useEffect(() => {
    if (parsedDocument && !text) {
      setText(parsedDocument.text);
      setDocName(parsedDocument.title || parsedDocument.filename);
    }
  }, [parsedDocument]);

  useEffect(() => {
    listRubrics({ token }).then((data) => {
      setRubrics(data);
      const def = data.find((r) => r.is_default);
      if (def) setSelectedRubricId(def.id);
    }).catch(() => {});
  }, [token]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      setText(ev.target?.result as string);
      setDocName(file.name.replace(/\.[^.]+$/, ""));
    };
    reader.readAsText(file);
  };

  const handleSharePointSelect = async (file: SharePointFile, libraryId: string) => {
    setSpLoading(true);
    setError(null);
    try {
      const parsed = await sharePointDownloadAndParse(
        { library_id: libraryId, item_id: file.id, filename: file.name },
        { token, llmProvider: llmProvider },
      );
      setText(parsed.document.text);
      setDocName(parsed.document.title || file.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load file from SharePoint.");
    } finally {
      setSpLoading(false);
    }
  };

  const handleRun = async () => {
    if (!text.trim() || !docName.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setShowRewrite(false);
    setAppliedRewrite(false);
    try {
      const res = await validateDocument(
        {
          text,
          document_name: docName,
          rubric_id: selectedRubricId,
          llm_provider: llmProvider,
          llm_model: llmModel || null,
        },
        { token },
      );
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validation failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleApplyRewrite = () => {
    if (result?.rewritten_text) {
      setText(result.rewritten_text);
      setAppliedRewrite(true);
    }
  };

  const totalIssues = (result?.layer1.issues.length ?? 0) + (result?.layer2.consistency_issues.length ?? 0);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <ClipboardCheck size={20} color="var(--bsbi-red)" style={{ marginRight: 8 }} />
          Narrative Validation
        </h1>
        <p className="page-subtitle">
          Run AI-powered quality checks against a rubric. Get a score, issue list, and an improved rewrite.
        </p>
      </div>

      <div className="validate-layout">
        {/* ── LEFT: Input ──────────────────────────────────────────────────── */}
        <div className="validate-input-col">
          <div className="card">
            <h3 className="card-title">Document Input</h3>

            {/* Source toggle */}
            <div className="source-toggle">
              <button
                type="button"
                className={`source-btn${source === "manual" ? " active" : ""}`}
                onClick={() => setSource("manual")}
              >
                <FileText size={14} /> Manual
              </button>
              <button
                type="button"
                className={`source-btn${source === "sharepoint" ? " active" : ""}`}
                onClick={() => setSource("sharepoint")}
              >
                <UploadCloud size={14} /> SharePoint
              </button>
            </div>

            {source === "manual" ? (
              <div className="validate-manual-input">
                <label className="form-label">Upload a text file (optional)</label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.md"
                  style={{ display: "none" }}
                  onChange={handleFileUpload}
                />
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ marginBottom: 12 }}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <UploadCloud size={14} /> Browse File
                </button>
              </div>
            ) : (
              <div style={{ marginBottom: 12 }}>
                {spLoading ? (
                  <div className="sp-picker sp-picker-status">
                    <Loader2 size={14} className="spin" /> Loading from SharePoint…
                  </div>
                ) : (
                  <SharePointPicker
                    token={token}
                    onSelect={handleSharePointSelect}
                    acceptExtensions={[".txt", ".md", ".docx", ".pdf"]}
                    disabled={loading}
                  />
                )}
              </div>
            )}

            <label className="form-label">Document Name</label>
            <input
              className="form-control"
              style={{ marginBottom: 12 }}
              placeholder="e.g. Q3 Project Update"
              value={docName}
              onChange={(e) => setDocName(e.target.value)}
            />

            <label className="form-label">Document Text</label>
            <textarea
              className="form-control validate-textarea"
              rows={10}
              placeholder="Paste or type the document text to validate…"
              value={text}
              onChange={(e) => setText(e.target.value)}
            />

            <label className="form-label" style={{ marginTop: 12 }}>Validation Rubric</label>
            <select
              className="form-control"
              style={{ marginBottom: 16 }}
              value={selectedRubricId ?? ""}
              onChange={(e) => setSelectedRubricId(e.target.value ? Number(e.target.value) : null)}
            >
              {rubrics.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}{r.is_default ? " (default)" : ""}
                </option>
              ))}
            </select>

            {error && (
              <div className="message error" style={{ marginBottom: 12 }}>
                <AlertCircle size={14} /> {error}
              </div>
            )}

            <button
              type="button"
              className="btn btn-primary"
              style={{ width: "100%" }}
              onClick={() => void handleRun()}
              disabled={loading || !text.trim() || !docName.trim()}
            >
              {loading ? <><Loader2 size={14} className="spin" /> Analysing…</> : <><RefreshCw size={14} /> Run AI Checks</>}
            </button>
          </div>
        </div>

        {/* ── RIGHT: Results ────────────────────────────────────────────────── */}
        <div className="validate-results-col">
          {!result && !loading && (
            <div className="validate-empty">
              <ClipboardCheck size={40} strokeWidth={1.2} />
              <h2>No results yet</h2>
              <p>Enter a document and click Run AI Checks to see quality scores and suggested improvements.</p>
              <div className="validate-legend">
                <span className="verdict-badge verdict-pass"><CheckCircle2 size={12} /> 8–10 Pass</span>
                <span className="verdict-badge verdict-warn"><AlertCircle size={12} /> 6–7 Warnings</span>
                <span className="verdict-badge verdict-fail"><XCircle size={12} /> &lt;6 Fail</span>
              </div>
            </div>
          )}

          {loading && (
            <div className="validate-empty">
              <Loader2 size={36} className="spin" />
              <h2>Analysing document…</h2>
              <p>Running Layer 1 (quality) and Layer 2 (consistency) checks.</p>
            </div>
          )}

          {result && (
            <div className="validate-results">
              {/* Verdict header */}
              <div className="card validate-verdict-card">
                <div className="validate-verdict-row">
                  <VerdictBadge verdict={result.overall_verdict} />
                  <ScoreRing score={result.layer1.compliance_score} />
                </div>
                <div className="validate-verdict-meta">
                  <span>{result.meta.rubric_name}</span>
                  <span>·</span>
                  <span>{totalIssues} issue{totalIssues !== 1 ? "s" : ""} found</span>
                  {result.meta.chunks_used > 0 && (
                    <>
                      <span>·</span>
                      <span>{result.meta.chunks_used} similar docs referenced</span>
                    </>
                  )}
                </div>
              </div>

              {/* Layer 1 issues */}
              {result.layer1.issues.length > 0 && (
                <div className="card validate-issues-card validate-issues-fail">
                  <h4 className="validate-issues-title"><XCircle size={14} /> Structure & Quality Issues</h4>
                  <ul className="validate-issues-list">
                    {result.layer1.issues.map((issue, i) => <li key={i}>{issue}</li>)}
                  </ul>
                </div>
              )}

              {/* Layer 1 passed */}
              {result.layer1.passed.length > 0 && (
                <div className="card validate-issues-card validate-issues-pass">
                  <h4 className="validate-issues-title"><CheckCircle2 size={14} /> Criteria Met</h4>
                  <ul className="validate-issues-list">
                    {result.layer1.passed.map((p, i) => <li key={i}>{p}</li>)}
                  </ul>
                </div>
              )}

              {/* Layer 2 consistency */}
              {result.layer2.consistency_issues.length > 0 && (
                <div className="card validate-issues-card validate-issues-warn">
                  <h4 className="validate-issues-title"><AlertCircle size={14} /> Consistency Issues</h4>
                  <ul className="validate-issues-list">
                    {result.layer2.consistency_issues.map((issue, i) => <li key={i}>{issue}</li>)}
                  </ul>
                </div>
              )}

              {/* AI Rewrite */}
              {result.rewritten_text && (
                <div className="card validate-rewrite-card">
                  <button
                    type="button"
                    className="validate-rewrite-toggle"
                    onClick={() => setShowRewrite((v) => !v)}
                  >
                    <span>✨ AI Suggested Rewrite</span>
                    <ChevronDown size={14} className={showRewrite ? "chevron-up" : ""} />
                  </button>

                  {showRewrite && (
                    <div className="validate-rewrite-body">
                      <DiffText original={text} rewritten={result.rewritten_text} />
                      <button
                        type="button"
                        className="btn btn-primary"
                        style={{ marginTop: 12 }}
                        onClick={handleApplyRewrite}
                        disabled={appliedRewrite}
                      >
                        {appliedRewrite ? <><CheckCircle2 size={14} /> Applied</> : "Use This Rewrite"}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ValidateView;