import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  FileText,
  Loader2,
  RefreshCw,
  Share2,
  Sparkles,
  Upload,
  X,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ModelControlBar from "../components/ModelControlBar";
import SharePointPicker from "../components/SharePointPicker";
import { useAppState } from "../context/AppStateContext";
import {
  extractRowsFromFile,
  extractRowsFromSharePoint,
  extractTextFromFile,
  extractTextFromSharePoint,
  scoreNarrative,
} from "../services/api";
import type { ExcelRowRecord, LLMProvider, NarrativeScoreResult, SharePointFile } from "../types/app";
import { wordDiff } from "../utils/diff";

type InputTab = "paste" | "local" | "sharepoint";

const VerdictBadge = ({ verdict }: { verdict: string }) => {
  if (verdict === "PASS") return <span className="verdict-badge verdict-pass"><CheckCircle2 size={13} /> PASS</span>;
  if (verdict === "PASS_WITH_WARNINGS") return <span className="verdict-badge verdict-warn"><AlertCircle size={13} /> PASS WITH WARNINGS</span>;
  return <span className="verdict-badge verdict-fail"><XCircle size={13} /> FAIL</span>;
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

const SeverityBadge = ({ severity }: { severity: string }) => (
  <span className={`abnormality-tag abnormality-${severity}`}>{severity}</span>
);

function DiffView({ oldText, newText }: { oldText: string; newText: string }) {
  const parts = wordDiff(oldText, newText);
  return (
    <div className="diff-view">
      {parts.map((p, i) =>
        p.added ? (
          <span key={i} className="diff-added">{p.value}</span>
        ) : p.removed ? (
          <span key={i} className="diff-removed">{p.value}</span>
        ) : (
          <span key={i}>{p.value}</span>
        )
      )}
    </div>
  );
}

export default function NarrativeView() {
  const { token, llmProvider, llmModel, rubrics, setProvider } = useAppState();

  const [inputTab, setInputTab] = useState<InputTab>("paste");
  const [uniqueId, setUniqueId] = useState("");
  const [docName, setDocName] = useState("");
  const [narrative, setNarrative] = useState("");
  const [selectedRubricId, setSelectedRubricId] = useState<number | null>(null);
  const [topK, setTopK] = useState(5);
  const [provider, setLocalProvider] = useState<LLMProvider>(llmProvider);
  const [model, setModel] = useState<string | null>(llmModel);
  const [result, setResult] = useState<NarrativeScoreResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRewrite, setShowRewrite] = useState(false);
  const [diffMode, setDiffMode] = useState(true);
  const [appliedRewrite, setAppliedRewrite] = useState(false);
  const [localFile, setLocalFile] = useState<File | null>(null);

  // Excel multi-project state
  const [excelRows, setExcelRows] = useState<ExcelRowRecord[] | null>(null);
  const [selectedRowId, setSelectedRowId] = useState<string>("");
  const [originalNarrative, setOriginalNarrative] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (rubrics.length > 0 && selectedRubricId === null) {
      const def = rubrics.find((r) => r.is_default);
      if (def) setSelectedRubricId(def.id);
    }
  }, [rubrics]);

  useEffect(() => {
    setLocalProvider(llmProvider);
    setModel(llmModel);
  }, [llmProvider, llmModel]);

  const handleProviderChange = (p: LLMProvider, m: string | null) => {
    setLocalProvider(p);
    setModel(m);
    setProvider(p, m);
  };

  const handleLocalFile = async (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    setLocalFile(file);
    setError(null);
    setExcelRows(null);
    setSelectedRowId("");

    if (["xlsx", "xls", "csv"].includes(ext)) {
      setExtracting(true);
      try {
        const res = await extractRowsFromFile(file, { token });
        if (res.rows.length === 0) {
          setError("No valid rows found in the file. Ensure it has an ID column and a narrative/text column.");
          return;
        }
        setExcelRows(res.rows);
        const first = res.rows[0];
        setSelectedRowId(first.id);
        setUniqueId(first.id);
        setDocName(file.name.replace(/\.[^.]+$/, ""));
        setNarrative(first.narrative);
        setOriginalNarrative(first.narrative);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to parse file.");
      } finally {
        setExtracting(false);
      }
      return;
    }

    setDocName(file.name.replace(/\.[^.]+$/, ""));
    setExtracting(true);
    try {
      const res = await extractTextFromFile(file, { token });
      setNarrative(res.text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to extract text.");
    } finally {
      setExtracting(false);
    }
  };

  const handleExcelRowSelect = (rowId: string) => {
    if (!excelRows) return;
    const row = excelRows.find((r) => r.id === rowId);
    if (!row) return;
    setSelectedRowId(rowId);
    setUniqueId(row.id);
    setNarrative(row.narrative);
    setOriginalNarrative(row.narrative);
  };

  const handleSharePointSelect = async (file: SharePointFile, libraryId: string) => {
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    setDocName(file.name.replace(/\.[^.]+$/, ""));
    setExtracting(true);
    setError(null);
    setExcelRows(null);
    setSelectedRowId("");
    try {
      if (["xlsx", "xls", "csv"].includes(ext)) {
        const res = await extractRowsFromSharePoint(
          { library_id: libraryId, item_id: file.id, filename: file.name },
          { token }
        );
        if (res.rows.length === 0) {
          setError("No valid rows found. Ensure the file has an ID column and a narrative/text column.");
          return;
        }
        setExcelRows(res.rows);
        const first = res.rows[0];
        setSelectedRowId(first.id);
        setUniqueId(first.id);
        setNarrative(first.narrative);
        setOriginalNarrative(first.narrative);
      } else {
        const res = await extractTextFromSharePoint(
          { library_id: libraryId, item_id: file.id, filename: file.name },
          { token }
        );
        setNarrative(res.text);
        setOriginalNarrative(res.text);
        setInputTab("paste");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to extract file from SharePoint.");
    } finally {
      setExtracting(false);
    }
  };

  const handleRun = async () => {
    if (!narrative.trim() || !uniqueId.trim()) return;
    abortRef.current = new AbortController();
    setLoading(true);
    setError(null);
    setResult(null);
    setShowRewrite(false);
    setAppliedRewrite(false);
    setOriginalNarrative(narrative);
    try {
      const res = await scoreNarrative(
        {
          narrative,
          unique_id: uniqueId,
          document_name: docName || uniqueId,
          rubric_id: selectedRubricId,
          llm_provider: provider,
          llm_model: model,
          top_k_references: topK,
        },
        { token, signal: abortRef.current.signal }
      );
      setResult(res);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError(err instanceof Error ? err.message : "Scoring failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    abortRef.current?.abort();
    setLoading(false);
  };

  const totalIssues = (result?.layer1.issues.length ?? 0) + (result?.layer2.abnormalities.length ?? 0);

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <Sparkles size={20} color="var(--bsbi-red)" />
          Score Narrative
        </h1>
        <p className="page-subtitle">
          Enter a narrative text to receive a quality score, abnormality flags, and an AI-suggested rewrite.
        </p>
      </div>

      <div className="two-col">
        {/* LEFT: Input */}
        <div>
          <div className="card" style={{ marginBottom: 14 }}>
            <h3 className="card-title">Narrative Input</h3>

            <label className="form-label">Unique ID *</label>
            <input
              className="form-control"
              style={{ marginBottom: 12 }}
              placeholder="e.g. PROJ-001 or P07|Security Systems"
              value={uniqueId}
              onChange={(e) => setUniqueId(e.target.value)}
            />

            <label className="form-label">Document Name (optional)</label>
            <input
              className="form-control"
              style={{ marginBottom: 12 }}
              placeholder="Human-readable project name"
              value={docName}
              onChange={(e) => setDocName(e.target.value)}
            />

            {/* Input method tabs */}
            <div className="input-tabs" style={{ marginBottom: 12 }}>
              <button
                type="button"
                className={`input-tab${inputTab === "paste" ? " active" : ""}`}
                onClick={() => setInputTab("paste")}
              >
                <FileText size={13} /> Paste Text
              </button>
              <button
                type="button"
                className={`input-tab${inputTab === "local" ? " active" : ""}`}
                onClick={() => setInputTab("local")}
              >
                <Upload size={13} /> Local File
              </button>
              <button
                type="button"
                className={`input-tab${inputTab === "sharepoint" ? " active" : ""}`}
                onClick={() => setInputTab("sharepoint")}
              >
                <Share2 size={13} /> SharePoint
              </button>
            </div>

            {/* Paste tab */}
            {inputTab === "paste" && (
              <textarea
                className="form-control"
                rows={10}
                placeholder="Paste or type the narrative text to score…"
                value={narrative}
                onChange={(e) => setNarrative(e.target.value)}
                style={{ marginBottom: 12 }}
              />
            )}

            {/* Local file tab */}
            {inputTab === "local" && (
              <div style={{ marginBottom: 12 }}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".txt,.docx,.pdf,.xlsx,.xls,.csv"
                  style={{ display: "none" }}
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) void handleLocalFile(f); }}
                />
                <div
                  className={`dropzone${localFile ? " dropzone-loaded" : ""}`}
                  onClick={() => fileInputRef.current?.click()}
                  style={{ marginBottom: 8 }}
                >
                  {extracting ? (
                    <><Loader2 size={18} className="spin" /><span>Extracting text…</span></>
                  ) : localFile ? (
                    <><FileText size={18} color="var(--bsbi-red)" />
                      <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>{localFile.name}</span>
                      <span className="dropzone-hint">Click to change</span></>
                  ) : (
                    <><Upload size={20} /><span>Click to upload a document</span>
                      <span className="dropzone-hint">.txt · .docx · .pdf · .xlsx · .csv</span></>
                  )}
                </div>

                {excelRows && excelRows.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <label className="form-label">Select Project</label>
                    <select
                      className="form-control"
                      value={selectedRowId}
                      onChange={(e) => handleExcelRowSelect(e.target.value)}
                      style={{ marginBottom: 4 }}
                    >
                      {excelRows.map((row) => (
                        <option key={row.id} value={row.id}>{row.id}</option>
                      ))}
                    </select>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 10 }}>
                      {excelRows.length} project{excelRows.length !== 1 ? "s" : ""} found · selecting populates the narrative
                    </div>
                    <label className="form-label">Narrative</label>
                    <textarea
                      className="form-control"
                      rows={7}
                      value={narrative}
                      onChange={(e) => setNarrative(e.target.value)}
                      style={{ fontSize: "0.84rem" }}
                    />
                  </div>
                )}

                {narrative && localFile && !excelRows && (
                  <div className="message success" style={{ fontSize: "0.8rem" }}>
                    <CheckCircle2 size={13} /> {narrative.length.toLocaleString()} characters extracted — switch to "Paste Text" to review or edit.
                  </div>
                )}
              </div>
            )}

            {/* SharePoint tab */}
            {inputTab === "sharepoint" && (
              <div style={{ marginBottom: 12 }}>
                {/* Always mount picker, hide during extraction to prevent reconnection */}
                <div style={{ display: extracting ? "none" : "block" }}>
                  <SharePointPicker
                    token={token}
                    acceptExtensions={[".txt", ".docx", ".pdf", ".xlsx", ".xls", ".csv"]}
                    onSelect={(file, libraryId) => void handleSharePointSelect(file, libraryId)}
                  />
                </div>
                {extracting && (
                  <div className="sp-picker sp-picker-status">
                    <Loader2 size={16} className="spin" /><span>Extracting text from SharePoint file…</span>
                  </div>
                )}

                {excelRows && excelRows.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <label className="form-label">Select Project</label>
                    <select
                      className="form-control"
                      value={selectedRowId}
                      onChange={(e) => handleExcelRowSelect(e.target.value)}
                      style={{ marginBottom: 4 }}
                    >
                      {excelRows.map((row) => (
                        <option key={row.id} value={row.id}>{row.id}</option>
                      ))}
                    </select>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 10 }}>
                      {excelRows.length} project{excelRows.length !== 1 ? "s" : ""} found · selecting populates the narrative
                    </div>
                    <label className="form-label">Narrative</label>
                    <textarea
                      className="form-control"
                      rows={7}
                      value={narrative}
                      onChange={(e) => setNarrative(e.target.value)}
                      style={{ fontSize: "0.84rem" }}
                    />
                  </div>
                )}

                {narrative && !extracting && !excelRows && (
                  <div className="message success" style={{ fontSize: "0.8rem", marginTop: 8 }}>
                    <CheckCircle2 size={13} /> {narrative.length.toLocaleString()} characters extracted — switch to "Paste Text" to review or edit.
                  </div>
                )}
              </div>
            )}

            <label className="form-label">Rubric</label>
            <select
              className="form-control"
              style={{ marginBottom: 12 }}
              value={selectedRubricId ?? ""}
              onChange={(e) => setSelectedRubricId(e.target.value ? Number(e.target.value) : null)}
            >
              {rubrics.map((r) => (
                <option key={r.id} value={r.id}>{r.name}{r.is_default ? " (default)" : ""}</option>
              ))}
            </select>

            <label className="form-label">Reference documents to compare</label>
            <input
              className="form-control"
              type="number" min={1} max={20} value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              style={{ marginBottom: 4 }}
            />
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: 14 }}>
              Retrieves the top <strong>{topK}</strong> most similar chunks from your{" "}
              <a href="/references" style={{ color: "var(--bsbi-red)" }}>Reference Library</a>{" "}
              to check patterns and detect abnormalities.
            </div>

            <div style={{ marginBottom: 14 }}>
              <ModelControlBar provider={provider} model={model} onChange={handleProviderChange} />
            </div>

            {error && (
              <div className="message error" style={{ marginBottom: 12 }}>
                <AlertCircle size={14} /> {error}
              </div>
            )}

            <div style={{ display: "flex", gap: 8 }}>
              <button
                type="button"
                className="btn btn-primary"
                style={{ flex: 1, justifyContent: "center" }}
                onClick={() => void handleRun()}
                disabled={loading || !narrative.trim() || !uniqueId.trim()}
              >
                {loading
                  ? <><Loader2 size={14} className="spin" /> Analysing…</>
                  : <><RefreshCw size={14} /> Run AI Score</>}
              </button>
              {loading && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handleCancel}
                  title="Cancel"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT: Results */}
        <div>
          {!result && !loading && (
            <div className="score-empty">
              <Sparkles size={40} strokeWidth={1.2} />
              <h2>No results yet</h2>
              <p>Enter a narrative ID, provide the text via any method, and click Run AI Score.</p>
              <div className="score-legend">
                <span className="verdict-badge verdict-pass"><CheckCircle2 size={12} /> 8–10 Pass</span>
                <span className="verdict-badge verdict-warn"><AlertCircle size={12} /> 6–7 Warnings</span>
                <span className="verdict-badge verdict-fail"><XCircle size={12} /> &lt;6 Fail</span>
              </div>
            </div>
          )}

          {loading && (
            <div className="score-empty">
              <Loader2 size={36} className="spin" />
              <h2>Analysing narrative…</h2>
              <p>Running Layer 1 (quality) and Layer 2 (reference comparison) checks.</p>
            </div>
          )}

          {result && (
            <div>
              <div className="card score-verdict-card" style={{ marginBottom: 14 }}>
                <div>
                  <VerdictBadge verdict={result.overall_verdict} />
                  <div className="score-verdict-meta">
                    <span>{result.meta.rubric_name}</span>
                    <span>·</span>
                    <span>{totalIssues} issue{totalIssues !== 1 ? "s" : ""}</span>
                    {result.meta.references_used > 0 && (
                      <><span>·</span><span>{result.meta.references_used} refs used</span></>
                    )}
                  </div>
                </div>
                <ScoreRing score={result.layer1.compliance_score} />
              </div>

              {result.layer1.issues.length > 0 && (
                <div className="card score-issues-card score-issues-fail" style={{ marginBottom: 12 }}>
                  <h4 className="score-issues-title"><XCircle size={13} /> Quality Issues</h4>
                  <ul className="score-issues-list">
                    {result.layer1.issues.map((issue, i) => <li key={i}>{issue}</li>)}
                  </ul>
                </div>
              )}

              {result.layer2.abnormalities.length > 0 && (
                <div className="card score-issues-card score-issues-warn" style={{ marginBottom: 12 }}>
                  <h4 className="score-issues-title"><AlertTriangle size={13} /> Abnormalities Detected</h4>
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {result.layer2.abnormalities.map((a, i) => (
                      <div key={i} style={{ fontSize: "0.85rem" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                          <SeverityBadge severity={a.severity} />
                          <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>{a.type.replace("_", " ")}</span>
                        </div>
                        <div>{a.description}</div>
                        {a.evidence && (
                          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", fontStyle: "italic", marginTop: 2 }}>
                            "{a.evidence}"
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.layer1.passed.length > 0 && (
                <div className="card score-issues-card score-issues-pass" style={{ marginBottom: 12 }}>
                  <h4 className="score-issues-title"><CheckCircle2 size={13} /> Criteria Met</h4>
                  <ul className="score-issues-list">
                    {result.layer1.passed.map((p, i) => <li key={i}>{p}</li>)}
                  </ul>
                </div>
              )}

              {result.layer2.patterns_followed.length > 0 && (
                <div className="card" style={{ marginBottom: 12, fontSize: "0.85rem" }}>
                  <h4 className="score-issues-title" style={{ marginBottom: 8 }}>Reference Patterns Followed</h4>
                  <ul className="score-issues-list" style={{ color: "var(--text-secondary)" }}>
                    {result.layer2.patterns_followed.map((p, i) => <li key={i}>{p}</li>)}
                  </ul>
                </div>
              )}

              {result.rewritten_narrative && (
                <div className="card">
                  <button type="button" className="rewrite-toggle" onClick={() => setShowRewrite((v) => !v)}>
                    <span>✨ AI Suggested Rewrite</span>
                    <ChevronDown size={14} className={showRewrite ? "chevron-up" : ""} />
                  </button>
                  {showRewrite && (
                    <div>
                      <div className="diff-toggle">
                        <button
                          type="button"
                          className={`diff-toggle-btn${diffMode ? " active" : ""}`}
                          onClick={() => setDiffMode(true)}
                        >
                          Diff View
                        </button>
                        <button
                          type="button"
                          className={`diff-toggle-btn${!diffMode ? " active" : ""}`}
                          onClick={() => setDiffMode(false)}
                        >
                          Full Text
                        </button>
                      </div>
                      {diffMode ? (
                        <DiffView oldText={originalNarrative} newText={result.rewritten_narrative} />
                      ) : (
                        <div className="rewrite-body">{result.rewritten_narrative}</div>
                      )}
                      <button
                        type="button"
                        className="btn btn-primary"
                        style={{ marginTop: 12 }}
                        onClick={() => {
                          setNarrative(result.rewritten_narrative);
                          setAppliedRewrite(true);
                          setInputTab("paste");
                        }}
                        disabled={appliedRewrite}
                      >
                        {appliedRewrite ? <><CheckCircle2 size={13} /> Applied</> : "Use This Rewrite"}
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
}