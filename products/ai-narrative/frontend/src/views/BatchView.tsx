import {
  AlertCircle,
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Download,
  FileSpreadsheet,
  Layers,
  Loader2,
  Share2,
  UploadCloud,
  X,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ModelControlBar from "../components/ModelControlBar";
import SharePointPicker from "../components/SharePointPicker";
import { useAppState } from "../context/AppStateContext";
import { detectColumns, downloadSharePointFile, scoreBatch } from "../services/api";
import type { ColumnDetectionResponse, LLMProvider, NarrativeScoreResult, SharePointFile } from "../types/app";
const verdictColour = (v: string) =>
  v === "PASS" ? "var(--status-pass)" : v === "PASS_WITH_WARNINGS" ? "var(--status-warn)" : "var(--status-fail)";

function exportCSV(results: NarrativeScoreResult[], rubricName: string) {
  const headers = ["ID", "Document Name", "Verdict", "Score", "Rubric", "Layer1 Issues", "Abnormalities", "AI Rewrite"];
  const rows = results.map((r) => [
    r.meta.unique_id, r.meta.document_name, r.overall_verdict,
    r.layer1.compliance_score.toFixed(1), rubricName,
    r.layer1.issues.join(" | "),
    r.layer2.abnormalities.map((a) => `[${a.severity}] ${a.description}`).join(" | "),
    r.rewritten_narrative || "",
  ]);
  const csv = [headers, ...rows].map((row) => row.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `AI_Narrative_Batch_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}

type BatchResult = NarrativeScoreResult & { _idx: number };
type Step = "upload" | "map" | "run";
type SourceTab = "local" | "sharepoint";

export default function BatchView() {
  const { token, llmProvider, llmModel, rubrics, setProvider } = useAppState();
  const [step, setStep] = useState<Step>("upload");
  const [sourceTab, setSourceTab] = useState<SourceTab>("local");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [provider, setLocalProvider] = useState<LLMProvider>(llmProvider);
  const [model, setModel] = useState<string | null>(llmModel);
  const [selectedRubricId, setSelectedRubricId] = useState<number | null>(null);
  const [topK, setTopK] = useState(5);

  const [detection, setDetection] = useState<ColumnDetectionResponse | null>(null);
  const [idColumn, setIdColumn] = useState<string>("");
  const [narrativeColumn, setNarrativeColumn] = useState<string>("");
  const [detectingCols, setDetectingCols] = useState(false);
  const [usingLlm, setUsingLlm] = useState(false);

  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<BatchResult[]>([]);
  const [rubricName, setRubricName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const [spDownloading, setSpDownloading] = useState(false);
  const [spFileSelected, setSpFileSelected] = useState(false);

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

  // Animate progress while running
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => {
      setProgress((p) => (p < 88 ? p + (88 - p) * 0.04 + 0.5 : p));
    }, 500);
    return () => clearInterval(timer);
  }, [running]);

  const handleProviderChange = (p: LLMProvider, m: string | null) => {
    setLocalProvider(p); setModel(m); setProvider(p, m);
  };

  const handleFileSelect = async (file: File) => {
    setSelectedFile(file);
    setDetection(null);
    setError(null);
    setStep("map");
    setDetectingCols(true);
    try {
      const result = await detectColumns(file, { token, useLlm: false, llmProvider: provider, llmModel: model });
      setDetection(result);
      setIdColumn(result.id_column ?? "");
      setNarrativeColumn(result.narrative_column ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Column detection failed.");
    } finally {
      setDetectingCols(false);
    }
  };

  const handleSharePointSelect = async (file: SharePointFile, libraryId: string) => {
    setSpDownloading(true);
    setError(null);
    try {
      const localFile = await downloadSharePointFile(libraryId, file.id, file.name, { token });
      await handleFileSelect(localFile);
      setSpFileSelected(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download file from SharePoint.");
    } finally {
      setSpDownloading(false);
    }
  };

  const handleAiDetect = async () => {
    if (!selectedFile) return;
    setDetectingCols(true);
    setUsingLlm(true);
    try {
      const result = await detectColumns(selectedFile, { token, useLlm: true, llmProvider: provider, llmModel: model });
      setDetection(result);
      setIdColumn(result.id_column ?? "");
      setNarrativeColumn(result.narrative_column ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI detection failed.");
    } finally {
      setDetectingCols(false);
      setUsingLlm(false);
    }
  };

  const handleRun = async () => {
    if (!selectedFile) return;
    abortRef.current = new AbortController();
    setStep("run");
    setRunning(true);
    setProgress(12);
    setError(null);
    setResults([]);
    setExpandedRows(new Set());
    try {
      const result = await scoreBatch(selectedFile, {
        token,
        rubricId: selectedRubricId,
        llmProvider: provider,
        llmModel: model,
        topKReferences: topK,
        idColumn: idColumn || undefined,
        narrativeColumn: narrativeColumn || undefined,
        signal: abortRef.current.signal,
      });
      setProgress(100);
      setRubricName(result.rubric_name);
      setResults(result.results.map((r, i) => ({ ...r, _idx: i })));
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        setStep("map");
        return;
      }
      setError(err instanceof Error ? err.message : "Batch scoring failed.");
      setStep("map");
    } finally {
      setRunning(false);
    }
  };

  const handleCancel = () => {
    abortRef.current?.abort();
    setRunning(false);
    setStep("map");
  };

  const toggleRow = (idx: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  const passCount = results.filter((r) => r.overall_verdict === "PASS").length;
  const warnCount = results.filter((r) => r.overall_verdict === "PASS_WITH_WARNINGS").length;
  const failCount = results.filter((r) => ["FAIL", "ERROR"].includes(r.overall_verdict)).length;

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title"><Layers size={20} color="var(--bsbi-red)" /> Batch Score</h1>
        <p className="page-subtitle">
          Upload an Excel or CSV file. Each row with a unique ID and narrative is scored independently.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 20 }}>
        {/* LEFT: Setup */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

          {/* Step 1 */}
          <div className="card" style={{ alignSelf: "start" }}>
            <h3 className="card-title">
              <span className={`step-indicator${step !== "upload" ? " step-done" : ""}`}>
                {step !== "upload" ? "✓" : "1"}
              </span>
              Upload File
            </h3>

            {/* Source tabs */}
            <div className="input-tabs" style={{ marginBottom: 10 }}>
              <button
                type="button"
                className={`input-tab${sourceTab === "local" ? " active" : ""}`}
                onClick={() => setSourceTab("local")}
              >
                <UploadCloud size={13} /> Local File
              </button>
              <button
                type="button"
                className={`input-tab${sourceTab === "sharepoint" ? " active" : ""}`}
                onClick={() => setSourceTab("sharepoint")}
              >
                <Share2 size={13} /> SharePoint
              </button>
            </div>

            {/* Local upload */}
            {sourceTab === "local" && (
              <div
                className={`dropzone${selectedFile ? " dropzone-loaded" : ""}`}
                style={{ marginBottom: 0 }}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv,.docx,.pdf"
                  style={{ display: "none" }}
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) void handleFileSelect(f); }}
                />
                {selectedFile && sourceTab === "local" ? (
                  <><FileSpreadsheet size={20} color="var(--bsbi-red)" />
                    <span style={{ fontWeight: 600, fontSize: "0.85rem" }}>{selectedFile.name}</span>
                    <span className="dropzone-hint">Click to change</span></>
                ) : (
                  <><UploadCloud size={24} /><span>Click to upload file</span>
                    <span className="dropzone-hint">.xlsx · .xls · .csv · .docx · .pdf</span></>
                )}
              </div>
            )}

            {/* SharePoint picker */}
            {sourceTab === "sharepoint" && (
              <div>
                {spDownloading && (
                  <div className="sp-picker sp-picker-status">
                    <Loader2 size={16} className="spin" /><span>Downloading file from SharePoint…</span>
                  </div>
                )}
                {/* Collapse picker once a file is loaded; show compact status + re-select button */}
                {!spDownloading && spFileSelected && selectedFile ? (
                  <div className="message success" style={{ fontSize: "0.82rem", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span><CheckCircle2 size={13} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />{selectedFile.name}</span>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ padding: "3px 8px", fontSize: "0.72rem" }}
                      onClick={() => { setSpFileSelected(false); setSelectedFile(null); setStep("upload"); setDetection(null); }}
                    >
                      Change
                    </button>
                  </div>
                ) : !spDownloading && (
                  <SharePointPicker
                    token={token}
                    acceptExtensions={[".xlsx", ".xls", ".csv", ".docx", ".pdf"]}
                    onSelect={(file, libraryId) => void handleSharePointSelect(file, libraryId)}
                    disabled={spDownloading}
                  />
                )}
              </div>
            )}
          </div>

          {/* After run: compact summary replaces steps 2 & 3 */}
          {step === "run" && results.length > 0 && (
            <div className="card" style={{ alignSelf: "start", fontSize: "0.82rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ fontWeight: 700, fontSize: "0.85rem" }}>Run Complete</span>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: "3px 10px", fontSize: "0.75rem" }}
                  onClick={() => { setStep("upload"); setSelectedFile(null); setDetection(null); setResults([]); setSpFileSelected(false); setError(null); }}
                >
                  New Batch
                </button>
              </div>
              <div style={{ color: "var(--text-muted)", display: "flex", flexDirection: "column", gap: 4 }}>
                <div><strong>File:</strong> {selectedFile?.name}</div>
                <div><strong>ID column:</strong> {idColumn}</div>
                <div><strong>Narrative column:</strong> {narrativeColumn}</div>
                <div><strong>Rubric:</strong> {rubricName}</div>
                <div><strong>Rows scored:</strong> {results.length}</div>
              </div>
            </div>
          )}

          {/* Step 2: Column mapping */}
          {step === "map" && selectedFile && (
            <div className="card" style={{ alignSelf: "start" }}>
              <h3 className="card-title">
                <span className="step-indicator">2</span>
                Confirm Columns
              </h3>

              {detectingCols ? (
                <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  <Loader2 size={14} className="spin" />
                  {usingLlm ? "AI is analysing your columns…" : "Detecting columns…"}
                </div>
              ) : detection ? (
                <>
                  {detection.ambiguous && (
                    <div className="message warning" style={{ marginBottom: 10, fontSize: "0.8rem" }}>
                      <AlertTriangle size={13} /> Multiple similar columns found — please verify the selection below.
                    </div>
                  )}

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      Method: <strong>{detection.method}</strong>
                    </span>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ padding: "3px 10px", fontSize: "0.75rem", gap: 5 }}
                      onClick={() => void handleAiDetect()}
                      disabled={detectingCols}
                    >
                      <Bot size={12} /> AI Detection
                    </button>
                  </div>

                  <label className="form-label">ID Column</label>
                  <select
                    className="form-control"
                    style={{ marginBottom: 6 }}
                    value={idColumn}
                    onChange={(e) => setIdColumn(e.target.value)}
                  >
                    <option value="">— select column —</option>
                    {detection.all_columns.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>

                  {idColumn && (() => {
                    const cand = detection.id_candidates.find(c => c.name === idColumn);
                    return cand && cand.sample.length > 0 ? (
                      <div className="col-sample" style={{ marginBottom: 10 }}>
                        {cand.sample.map((s, i) => <span key={i} className="col-sample-chip">{s}</span>)}
                      </div>
                    ) : null;
                  })()}

                  <label className="form-label">Narrative Column</label>
                  <select
                    className="form-control"
                    style={{ marginBottom: 6 }}
                    value={narrativeColumn}
                    onChange={(e) => setNarrativeColumn(e.target.value)}
                  >
                    <option value="">— select column —</option>
                    {detection.all_columns.filter(c => c !== idColumn).map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>

                  {narrativeColumn && (() => {
                    const cand = detection.narrative_candidates.find(c => c.name === narrativeColumn);
                    return cand && cand.sample.length > 0 ? (
                      <div className="col-sample" style={{ marginBottom: 4 }}>
                        {cand.sample.map((s, i) => (
                          <span key={i} className="col-sample-chip col-sample-chip-long">{s}</span>
                        ))}
                      </div>
                    ) : null;
                  })()}
                </>
              ) : null}
            </div>
          )}

          {/* Step 3: Scoring config */}
          {step === "map" && !detectingCols && (
            <div className="card" style={{ alignSelf: "start" }}>
              <h3 className="card-title">
                <span className="step-indicator">3</span>
                Scoring Options
              </h3>

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
                per narrative.
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
                  disabled={running || !selectedFile || !idColumn || !narrativeColumn}
                  onClick={() => void handleRun()}
                >
                  {running
                    ? <><Loader2 size={14} className="spin" /> Scoring…</>
                    : <><Layers size={14} /> Run Batch Score</>}
                </button>
                {running && (
                  <button type="button" className="btn btn-secondary" onClick={handleCancel} title="Cancel">
                    <X size={14} />
                  </button>
                )}
              </div>

              {(!idColumn || !narrativeColumn) && !running && (
                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 8, textAlign: "center" }}>
                  Select both ID and Narrative columns above to continue.
                </p>
              )}

              {running && (
                <div className="batch-progress-wrap">
                  <div className="batch-progress-bar" style={{ width: `${progress}%` }} />
                </div>
              )}
            </div>
          )}
        </div>

        {/* RIGHT: Results */}
        <div>
          {results.length === 0 && !running ? (
            <div className="score-empty">
              <Layers size={40} strokeWidth={1.2} />
              <h2>No results yet</h2>
              <p>Upload an Excel/CSV, confirm the column mapping, then click Run Batch Score.</p>
              <div className="score-legend">
                <span className="verdict-badge verdict-pass"><CheckCircle2 size={12} /> 8–10 Pass</span>
                <span className="verdict-badge verdict-warn"><AlertCircle size={12} /> 6–7 Warnings</span>
                <span className="verdict-badge verdict-fail"><XCircle size={12} /> &lt;6 Fail</span>
              </div>
            </div>
          ) : (
            <>
              <div className="batch-results-header">
                <div className="batch-stats">
                  {results.length > 0 && (
                    <>
                      <span className="batch-stat batch-stat-pass"><CheckCircle2 size={13} /> {passCount} Pass</span>
                      <span className="batch-stat batch-stat-warn"><AlertCircle size={13} /> {warnCount} Warn</span>
                      <span className="batch-stat batch-stat-fail"><XCircle size={13} /> {failCount} Fail</span>
                      <span className="batch-stat">Total: {results.length}</span>
                    </>
                  )}
                  {running && <span className="batch-stat"><Loader2 size={13} className="spin" /> Running…</span>}
                </div>
                {results.length > 0 && (
                  <button type="button" className="btn btn-secondary" onClick={() => exportCSV(results, rubricName)}>
                    <Download size={13} /> Export CSV
                  </button>
                )}
              </div>

              <div className="batch-table-wrap">
                <table className="batch-table">
                  <thead>
                    <tr>
                      <th style={{ width: 32 }} />
                      <th>ID</th>
                      <th>Document</th>
                      <th style={{ width: 120 }}>Verdict</th>
                      <th style={{ width: 56, textAlign: "center" }}>Score</th>
                      <th style={{ width: 56, textAlign: "center" }}>Issues</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r) => {
                      const expanded = expandedRows.has(r._idx);
                      const issueCount = r.layer1.issues.length + r.layer2.abnormalities.length;
                      return (
                        <>
                          <tr key={`row-${r._idx}`} className="batch-row" onClick={() => toggleRow(r._idx)}>
                            <td>{expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</td>
                            <td style={{ fontFamily: "monospace", fontSize: "0.8rem" }}>{r.meta.unique_id}</td>
                            <td>{r.meta.document_name}</td>
                            <td>
                              <span style={{ color: verdictColour(r.overall_verdict), fontWeight: 600, fontSize: "0.82rem" }}>
                                {r.overall_verdict === "PASS_WITH_WARNINGS" ? "WARN" : r.overall_verdict}
                              </span>
                            </td>
                            <td style={{ textAlign: "center" }}>
                              {!["SKIPPED", "ERROR"].includes(r.overall_verdict) ? r.layer1.compliance_score.toFixed(1) : "—"}
                            </td>
                            <td style={{ textAlign: "center" }}>{issueCount > 0 ? issueCount : "—"}</td>
                          </tr>
                          {expanded && (
                            <tr key={`detail-${r._idx}`} className="batch-detail-row">
                              <td colSpan={6}>
                                <div className="batch-detail-body">
                                  {r.layer1.issues.length > 0 && (
                                    <div className="batch-detail-section">
                                      <strong>Quality Issues</strong>
                                      <ul>{r.layer1.issues.map((i, k) => <li key={k}>{i}</li>)}</ul>
                                    </div>
                                  )}
                                  {r.layer2.abnormalities.length > 0 && (
                                    <div className="batch-detail-section">
                                      <strong>Abnormalities</strong>
                                      <ul>
                                        {r.layer2.abnormalities.map((a, k) => (
                                          <li key={k}>
                                            <span className={`abnormality-tag abnormality-${a.severity}`}>{a.severity}</span> {a.description}
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                  {r.layer1.passed.length > 0 && (
                                    <div className="batch-detail-section">
                                      <strong>Criteria Met</strong>
                                      <ul>{r.layer1.passed.map((p, k) => <li key={k}>{p}</li>)}</ul>
                                    </div>
                                  )}
                                  {r.rewritten_narrative && (
                                    <div className="batch-detail-section">
                                      <strong>✨ AI Suggested Rewrite</strong>
                                      <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: 4, whiteSpace: "pre-wrap" }}>
                                        {r.rewritten_narrative}
                                      </p>
                                    </div>
                                  )}
                                </div>
                              </td>
                            </tr>
                          )}
                        </>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}