import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Download,
  FileSpreadsheet,
  Layers,
  Loader2,
  UploadCloud,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import SharePointPicker from "../components/SharePointPicker";
import { useAppState } from "../context/AppStateContext";
import { getSharePointFiles, getSharePointLibraries, listRubrics, validateBatch } from "../services/api";
import type { RubricSummary, SharePointFile, ValidationResult } from "../types/app";

type Source = "local" | "sharepoint";

type BatchResult = ValidationResult & { _idx: number };

const verdictColour = (verdict: string) => {
  if (verdict === "PASS") return "var(--status-pass)";
  if (verdict === "PASS_WITH_WARNINGS") return "var(--status-warn)";
  return "var(--status-fail)";
};

const VerdictIcon = ({ verdict }: { verdict: string }) => {
  if (verdict === "PASS") return <CheckCircle2 size={14} color="var(--status-pass)" />;
  if (verdict === "PASS_WITH_WARNINGS") return <AlertCircle size={14} color="var(--status-warn)" />;
  if (verdict === "SKIPPED") return <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>SKIP</span>;
  if (verdict === "ERROR") return <XCircle size={14} color="var(--status-fail)" />;
  return <XCircle size={14} color="var(--status-fail)" />;
};

function exportToCSV(results: ValidationResult[], rubricName: string) {
  const headers = ["Document Name", "Verdict", "Score", "Rubric", "Layer 1 Issues", "Consistency Issues", "Rewrite Available"];
  const rows = results.map((r) => [
    r.meta.document_name,
    r.overall_verdict,
    r.layer1.compliance_score.toFixed(1),
    rubricName,
    r.layer1.issues.join(" | "),
    r.layer2.consistency_issues.join(" | "),
    r.rewritten_text ? "Yes" : "No",
  ]);

  const csv = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","))
    .join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `BSBI_Batch_Validation_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

const BatchValidateView = () => {
  const { token, llmProvider, llmModel } = useAppState();

  const [source, setSource] = useState<Source>("local");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [spFile, setSpFile] = useState<{ file: SharePointFile; libraryId: string } | null>(null);
  const [spFetching, setSpFetching] = useState(false);

  const [rubrics, setRubrics] = useState<RubricSummary[]>([]);
  const [selectedRubricId, setSelectedRubricId] = useState<number | null>(null);

  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState<BatchResult[]>([]);
  const [rubricName, setRubricName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    listRubrics({ token }).then((data) => {
      setRubrics(data);
      const def = data.find((r) => r.is_default);
      if (def) setSelectedRubricId(def.id);
    }).catch(() => {});
  }, [token]);

  const handleLocalFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) { setSelectedFile(file); setSpFile(null); }
  };

  const handleSpSelect = (file: SharePointFile, libraryId: string) => {
    setSpFile({ file, libraryId });
    setSelectedFile(null);
  };

  const handleRun = async () => {
    if (!selectedFile && !spFile) return;
    setRunning(true);
    setProgress(10);
    setError(null);
    setResults([]);

    try {
      let fileToSend: File;

      if (selectedFile) {
        fileToSend = selectedFile;
      } else if (spFile) {
        // Download from SharePoint
        setSpFetching(true);
        const { getSharePointFiles: _unused, ...rest } = { getSharePointFiles, ...{} };
        void _unused; void rest;
        // Use the Graph API download via our backend
        const response = await fetch(
          `/api/v1/sharepoint/files?library_id=${encodeURIComponent(spFile.libraryId)}&folder_path=/`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        // Actually download the file content bytes via the download endpoint
        const downloadResp = await fetch(`/api/v1/sharepoint/download-bytes`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ library_id: spFile.libraryId, item_id: spFile.file.id }),
        });
        setSpFetching(false);
        if (!downloadResp.ok) throw new Error("Failed to download file from SharePoint.");
        const blob = await downloadResp.blob();
        fileToSend = new File([blob], spFile.file.name);
      } else {
        return;
      }

      setProgress(30);
      const result = await validateBatch(fileToSend, {
        token,
        rubricId: selectedRubricId,
        llmProvider,
        llmModel: llmModel || null,
      });
      setProgress(100);
      setRubricName(result.rubric_name);
      setResults(result.results.map((r, i) => ({ ...r, _idx: i })));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Batch validation failed.");
    } finally {
      setRunning(false);
      setSpFetching(false);
    }
  };

  const toggleRow = (idx: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const passCount = results.filter((r) => r.overall_verdict === "PASS").length;
  const warnCount = results.filter((r) => r.overall_verdict === "PASS_WITH_WARNINGS").length;
  const failCount = results.filter((r) => r.overall_verdict === "FAIL" || r.overall_verdict === "ERROR").length;

  const fileLabel = selectedFile
    ? selectedFile.name
    : spFile
    ? spFile.file.name
    : null;

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <Layers size={20} color="var(--bsbi-red)" style={{ marginRight: 8 }} />
          Batch Validation
        </h1>
        <p className="page-subtitle">
          Upload an Excel or CSV file with multiple documents. Each row is validated individually.
          Required columns: <code>document_name</code>, <code>text</code> (or <code>narrative</code>/<code>content</code>).
        </p>
      </div>

      <div className="batch-layout">
        {/* ── LEFT: Setup ──────────────────────────────────────────────────── */}
        <div className="batch-input-col">
          <div className="card">
            <h3 className="card-title">Batch Setup</h3>

            {/* Source toggle */}
            <div className="source-toggle" style={{ marginBottom: 16 }}>
              <button
                type="button"
                className={`source-btn${source === "local" ? " active" : ""}`}
                onClick={() => setSource("local")}
              >
                <FileSpreadsheet size={14} /> Local Upload
              </button>
              <button
                type="button"
                className={`source-btn${source === "sharepoint" ? " active" : ""}`}
                onClick={() => setSource("sharepoint")}
              >
                <UploadCloud size={14} /> SharePoint
              </button>
            </div>

            {source === "local" ? (
              <div
                className={`dropzone batch-dropzone${fileLabel ? " batch-dropzone-loaded" : ""}`}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  style={{ display: "none" }}
                  onChange={handleLocalFile}
                />
                {fileLabel ? (
                  <>
                    <FileSpreadsheet size={20} color="var(--bsbi-red)" />
                    <span className="batch-loaded-name">{fileLabel}</span>
                    <span className="batch-loaded-change">Click to change</span>
                  </>
                ) : (
                  <>
                    <UploadCloud size={24} />
                    <span>Click to upload Excel / CSV</span>
                    <span className="dropzone-hint">.xlsx · .xls · .csv</span>
                  </>
                )}
              </div>
            ) : (
              <SharePointPicker
                token={token}
                onSelect={handleSpSelect}
                acceptExtensions={[".xlsx", ".xls", ".csv"]}
                disabled={running}
              />
            )}

            {spFile && (
              <div className="batch-sp-selected">
                <FileSpreadsheet size={14} /> {spFile.file.name}
              </div>
            )}

            <label className="form-label" style={{ marginTop: 16 }}>Validation Rubric</label>
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
              disabled={running || (!selectedFile && !spFile)}
              onClick={() => void handleRun()}
            >
              {running
                ? <><Loader2 size={14} className="spin" /> Validating…</>
                : <><Layers size={14} /> Run AI Checks</>}
            </button>

            {running && (
              <div className="batch-progress-wrap" style={{ marginTop: 12 }}>
                <div className="batch-progress-bar" style={{ width: `${progress}%` }} />
              </div>
            )}
          </div>
        </div>

        {/* ── RIGHT: Results ────────────────────────────────────────────────── */}
        <div className="batch-results-col">
          {results.length === 0 && !running ? (
            <div className="validate-empty">
              <Layers size={40} strokeWidth={1.2} />
              <h2>No results yet</h2>
              <p>Upload a file and click Run AI Checks. Each row will be validated independently.</p>
              <div className="validate-legend">
                <span className="verdict-badge verdict-pass"><CheckCircle2 size={12} /> 8–10 Pass</span>
                <span className="verdict-badge verdict-warn"><AlertCircle size={12} /> 6–7 Warnings</span>
                <span className="verdict-badge verdict-fail"><XCircle size={12} /> &lt;6 Fail</span>
              </div>
            </div>
          ) : (
            <>
              {/* Results header */}
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
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => exportToCSV(results, rubricName)}
                  >
                    <Download size={13} /> Export CSV
                  </button>
                )}
              </div>

              {/* Results table */}
              <div className="batch-table-wrap">
                <table className="batch-table">
                  <thead>
                    <tr>
                      <th style={{ width: 32 }} />
                      <th>Document Name</th>
                      <th style={{ width: 140 }}>Verdict</th>
                      <th style={{ width: 64, textAlign: "center" }}>Score</th>
                      <th style={{ width: 64, textAlign: "center" }}>Issues</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((r) => {
                      const expanded = expandedRows.has(r._idx);
                      const issueCount = r.layer1.issues.length + r.layer2.consistency_issues.length;
                      return (
                        <>
                          <tr
                            key={`row-${r._idx}`}
                            className="batch-row"
                            onClick={() => toggleRow(r._idx)}
                          >
                            <td className="batch-expand-cell">
                              {expanded
                                ? <ChevronDown size={14} />
                                : <ChevronRight size={14} />}
                            </td>
                            <td className="batch-name-cell">{r.meta.document_name}</td>
                            <td>
                              <span className="batch-verdict" style={{ color: verdictColour(r.overall_verdict) }}>
                                <VerdictIcon verdict={r.overall_verdict} />
                                {r.overall_verdict === "PASS_WITH_WARNINGS" ? "WARN" : r.overall_verdict}
                              </span>
                            </td>
                            <td className="batch-score-cell">
                              {r.overall_verdict !== "SKIPPED" && r.overall_verdict !== "ERROR"
                                ? r.layer1.compliance_score.toFixed(1)
                                : "—"}
                            </td>
                            <td className="batch-issues-cell">
                              {issueCount > 0 ? issueCount : "—"}
                            </td>
                          </tr>

                          {expanded && (
                            <tr key={`detail-${r._idx}`} className="batch-detail-row">
                              <td colSpan={5}>
                                <div className="batch-detail-body">
                                  {r.layer1.issues.length > 0 && (
                                    <div className="batch-detail-section batch-detail-fail">
                                      <strong>Structure & Quality Issues</strong>
                                      <ul>{r.layer1.issues.map((i, k) => <li key={k}>{i}</li>)}</ul>
                                    </div>
                                  )}
                                  {r.layer2.consistency_issues.length > 0 && (
                                    <div className="batch-detail-section batch-detail-warn">
                                      <strong>Consistency Issues</strong>
                                      <ul>{r.layer2.consistency_issues.map((i, k) => <li key={k}>{i}</li>)}</ul>
                                    </div>
                                  )}
                                  {r.layer1.passed.length > 0 && (
                                    <div className="batch-detail-section batch-detail-pass">
                                      <strong>Criteria Met</strong>
                                      <ul>{r.layer1.passed.map((p, k) => <li key={k}>{p}</li>)}</ul>
                                    </div>
                                  )}
                                  {r.rewritten_text && (
                                    <div className="batch-detail-section batch-detail-rewrite">
                                      <strong>✨ AI Rewrite Available</strong>
                                      <p className="batch-rewrite-preview">{r.rewritten_text.slice(0, 300)}{r.rewritten_text.length > 300 ? "…" : ""}</p>
                                    </div>
                                  )}
                                  {r.overall_verdict === "ERROR" && (
                                    <div className="batch-detail-section batch-detail-fail">
                                      <strong>Error</strong>
                                      <p>{r.layer1.issues[0] ?? "Unknown error"}</p>
                                    </div>
                                  )}
                                  {r.overall_verdict === "SKIPPED" && (
                                    <div className="batch-detail-section">
                                      <strong>Skipped</strong>
                                      <p>No text content provided for this document.</p>
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
};

export default BatchValidateView;