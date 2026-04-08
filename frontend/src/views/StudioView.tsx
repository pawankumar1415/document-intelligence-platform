import {
  AlertCircle,
  AlignLeft,
  CheckCircle2,
  Clipboard,
  ClipboardCheck,
  Cpu,
  Download,
  FileCheck2,
  FilePlus2,
  FileText,
  Loader2,
  Presentation,
  RotateCcw,
  UploadCloud,
  WandSparkles,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { useAppState } from "../context/AppStateContext";
import {
  ApiError,
  downloadArtifact,
  generateBid,
  generatePptx,
  generateSow,
  parseDocument,
  summarizeDocument,
} from "../services/api";
import type { SummarizeResponse, SummaryMode, UseCaseAssessment } from "../types/app";

type GenTab = "sow" | "ppt" | "summarize" | "bid";

const SUMMARY_MODES: { id: SummaryMode; label: string; desc: string }[] = [
  { id: "executive_summary", label: "Executive Summary", desc: "3-4 paragraph narrative covering context, scope, actions, and risks" },
  { id: "bullet_points",     label: "Bullet Points",     desc: "Grouped bullet points organised by theme" },
  { id: "narrative_rewrite", label: "Narrative Rewrite", desc: "Clean, flowing prose rewrite of the full document" },
  { id: "key_insights",      label: "Key Insights",      desc: "5-8 standalone insights ranked by significance" },
];

const StudioView = () => {
  const {
    addOutput,
    llmModel,
    llmProvider,
    outputs,
    parsedDocument,
    projectId,
    setParsedDocument,
    setProjectId,
    token,
  } = useAppState();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [projectName, setProjectName] = useState("BSBI Discovery Project");
  const [clientName, setClientName] = useState("BSBI Consulting");
  const [deckTitle, setDeckTitle] = useState("BSBI Document Intelligence Brief");
  const [subtitle, setSubtitle] = useState("Generated from uploaded document");
  const [assumptions, setAssumptions] = useState("");
  const [maxSlides, setMaxSlides] = useState(6);
  const [activeTab, setActiveTab] = useState<GenTab>("sow");

  const [parseLoading, setParseLoading] = useState(false);
  const [sowLoading, setSowLoading] = useState(false);
  const [pptLoading, setPptLoading] = useState(false);
  const [bidLoading, setBidLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [bidOpportunityTitle, setBidOpportunityTitle] = useState("Document Intelligence Platform Implementation");
  const [bidStrengths, setBidStrengths] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [useCaseAssessment, setUseCaseAssessment] = useState<UseCaseAssessment | null>(null);
  const [summaryMode, setSummaryMode] = useState<SummaryMode>("executive_summary");
  const [summaryResult, setSummaryResult] = useState<SummarizeResponse | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const summaryResultRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (summaryResult && summaryResultRef.current) {
      summaryResultRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [summaryResult]);

  const sowCount = outputs.filter((o) => o.artifact_type === "sow").length;
  const pptCount = outputs.filter((o) => o.artifact_type === "pptx").length;

  const handleFileChange = (file: File | null) => {
    setSelectedFile(file);
    setParseError(null);
  };

  const handleParse = async () => {
    if (!selectedFile) {
      setParseError("Select a .docx, .txt, or .pdf file before parsing.");
      return;
    }
    setParseLoading(true);
    setParseError(null);
    setGenerateError(null);
    setStatusMessage(null);
    setUseCaseAssessment(null);
    try {
      const response = await parseDocument(selectedFile, {
        token,
        projectName,
        llmProvider,
        projectId: projectId ?? undefined,
      });
      setParsedDocument(response.document);
      if (typeof response.project_id === "number") setProjectId(response.project_id);
      setUseCaseAssessment(response.use_case_assessment ?? null);
      setStatusMessage(
        `"${response.document.title}" parsed — ${response.document.word_count} words, ${response.document.sections.length} sections.`
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 422 && err.payload?.code === "unsupported_document") {
        setParseError(err.payload.message || "This document type is not supported.");
        setUseCaseAssessment(err.payload.assessment ?? null);
        setParsedDocument(null);
      } else {
        setParseError(err instanceof Error ? err.message : "Could not parse the document.");
      }
    } finally {
      setParseLoading(false);
    }
  };

  const handleGenerateSow = async () => {
    if (!parsedDocument) return;
    setSowLoading(true);
    setGenerateError(null);
    setStatusMessage(null);
    try {
      const response = await generateSow(
        {
          client_name: clientName,
          project_name: projectName,
          source_document: { title: parsedDocument.title, text: parsedDocument.text, sections: parsedDocument.sections },
          project_id: projectId ?? undefined,
          llm_provider: llmProvider,
          llm_model: llmModel || undefined,
          assumptions: assumptions.split("\n").map((l) => l.trim()).filter(Boolean),
        },
        { token },
      );
      addOutput(response);
      setStatusMessage("SOW generated successfully.");
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "Could not generate SOW.");
    } finally {
      setSowLoading(false);
    }
  };

  const handleGeneratePpt = async () => {
    if (!parsedDocument) return;
    setPptLoading(true);
    setGenerateError(null);
    setStatusMessage(null);
    try {
      const response = await generatePptx(
        {
          deck_title: deckTitle,
          subtitle,
          source_document: { title: parsedDocument.title, text: parsedDocument.text, sections: parsedDocument.sections },
          project_id: projectId ?? undefined,
          llm_provider: llmProvider,
          llm_model: llmModel || undefined,
          max_content_slides: maxSlides,
        },
        { token },
      );
      addOutput(response);
      setStatusMessage("Presentation generated successfully.");
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "Could not generate presentation.");
    } finally {
      setPptLoading(false);
    }
  };

  const handleSummarize = async () => {
    if (!parsedDocument) return;
    setSummaryLoading(true);
    setSummaryError(null);
    setSummaryResult(null);
    setCopied(false);
    try {
      const result = await summarizeDocument(
        {
          title: parsedDocument.title,
          source_text: parsedDocument.text,
          file_type: parsedDocument.file_type,
          extraction_signals: parsedDocument.extraction_signals,
          mode: summaryMode,
          llm_provider: llmProvider,
          llm_model: llmModel || undefined,
        },
        { token },
      );
      setSummaryResult(result);
    } catch (err) {
      setSummaryError(err instanceof Error ? err.message : "Summarization failed.");
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleGenerateBid = async () => {
    if (!parsedDocument) return;
    setBidLoading(true);
    setGenerateError(null);
    setStatusMessage(null);
    try {
      const response = await generateBid(
        {
          client_name: clientName,
          opportunity_title: bidOpportunityTitle,
          source_document: { title: parsedDocument.title, text: parsedDocument.text, sections: parsedDocument.sections },
          our_strengths: bidStrengths.split("\n").map((l) => l.trim()).filter(Boolean),
          project_id: projectId ?? undefined,
          llm_provider: llmProvider,
          llm_model: llmModel || undefined,
        },
        { token },
      );
      addOutput(response);
      setStatusMessage("Bid response generated successfully.");
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : "Could not generate bid response.");
    } finally {
      setBidLoading(false);
    }
  };

  const handleDownload = async (downloadUrl: string, artifactName: string) => {
    setDownloadError(null);
    try {
      await downloadArtifact(downloadUrl, artifactName, { token });
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : "Download failed.");
    }
  };

  const handleCopySummary = async () => {
    if (!summaryResult) return;
    const text = [
      summaryResult.title,
      summaryResult.summary_line,
      ...summaryResult.paragraphs,
      ...summaryResult.key_points.map((p) => `• ${p}`),
      ...summaryResult.groups.flatMap((g) => [`\n${g.heading}`, ...g.bullets.map((b) => `• ${b}`)]),
      ...summaryResult.insights.map((i) => `[${i.significance.toUpperCase()}] ${i.insight}`),
    ]
      .filter(Boolean)
      .join("\n\n");
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const anyError = parseError || generateError || downloadError;

  return (
    <div className="studio-page">
      {/* ── Status bar ── */}
      <div className="studio-bar">
        <div className="studio-bar-doc">
          {parsedDocument ? (
            <>
              <FileCheck2 size={14} className="studio-bar-icon ok" />
              <span className="studio-bar-label">
                <strong>{parsedDocument.title}</strong>
                <span className="studio-bar-meta">
                  {parsedDocument.file_type?.toUpperCase()} · {parsedDocument.word_count} words · {parsedDocument.sections.length} sections
                </span>
              </span>
            </>
          ) : (
            <>
              <UploadCloud size={14} className="studio-bar-icon dim" />
              <span className="studio-bar-label dim">No document loaded — upload one to start</span>
            </>
          )}
        </div>
        <div className="studio-bar-ai">
          <Cpu size={12} />
          <span>{llmProvider}</span>
          {llmModel && (
            <>
              <span className="studio-bar-sep">·</span>
              <span className="studio-bar-model">{llmModel}</span>
            </>
          )}
        </div>
      </div>

      {/* ── Feedback ── */}
      {statusMessage && (
        <div className="message success">
          <CheckCircle2 size={15} />
          <span>{statusMessage}</span>
        </div>
      )}
      {anyError && (
        <div className="message error">
          <AlertCircle size={15} />
          <span>{anyError}</span>
        </div>
      )}

      {/* ── Studio layout ── */}
      <div className="studio-layout">

        {/* ════ LEFT — Document ════ */}
        <article className="card studio-doc">
          <header className="step-header">
            <span className="step-badge">01</span>
            <div>
              <h2>Source Document</h2>
              <p className="step-desc">Upload a project brief, proposal, or requirements doc</p>
            </div>
          </header>

          <label className="field-label">
            Project name
            <input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g. BSBI Discovery Project"
            />
          </label>

          {!parsedDocument ? (
            <>
              <label className="dropzone">
                <input
                  type="file"
                  accept=".docx,.txt,.pdf"
                  onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
                />
                <UploadCloud size={34} strokeWidth={1.5} className="dropzone-icon" />
                <strong>Drop file here or click to browse</strong>
                <span>.docx · .txt · .pdf supported</span>
              </label>

              {selectedFile ? (
                <div className="selected-file-row">
                  <span className="selected-file-name">
                    <FileText size={14} />
                    {selectedFile.name}
                  </span>
                  <button
                    className="btn btn-primary"
                    type="button"
                    onClick={handleParse}
                    disabled={parseLoading}
                    style={{ padding: "7px 14px", fontSize: "0.82rem" }}
                  >
                    {parseLoading
                      ? <><Loader2 size={13} className="spin" /> Parsing…</>
                      : "Parse Document"
                    }
                  </button>
                </div>
              ) : (
                <p className="dropzone-hint">Select a file above, then click Parse to extract content.</p>
              )}
            </>
          ) : (
            <>
              <div className="doc-loaded-card">
                <div className="doc-loaded-icon">
                  <FileCheck2 size={20} />
                </div>
                <div className="doc-loaded-info">
                  <h3>{parsedDocument.title}</h3>
                  <p>{parsedDocument.file_type?.toUpperCase()} · {parsedDocument.filename}</p>
                </div>
              </div>

              <div className="doc-stats-row">
                <div className="doc-stat">
                  <span>Words</span>
                  <strong>{parsedDocument.word_count.toLocaleString()}</strong>
                </div>
                <div className="doc-stat">
                  <span>Sections</span>
                  <strong>{parsedDocument.sections.length}</strong>
                </div>
                <div className="doc-stat">
                  <span>Paragraphs</span>
                  <strong>{parsedDocument.paragraph_count}</strong>
                </div>
              </div>

              {parsedDocument.extraction_signals && parsedDocument.extraction_signals.length > 0 && (
                <div className="signal-chips">
                  {parsedDocument.extraction_signals.slice(0, 5).map((s) => (
                    <span key={s.name} className="signal-chip">
                      {s.name.replaceAll("_", " ")}
                    </span>
                  ))}
                </div>
              )}

              <label className="reupload-label">
                <input
                  type="file"
                  accept=".docx,.txt,.pdf"
                  onChange={(e) => {
                    handleFileChange(e.target.files?.[0] ?? null);
                    setParsedDocument(null);
                    setStatusMessage(null);
                  }}
                />
                <RotateCcw size={13} /> Replace document
              </label>
            </>
          )}

          {useCaseAssessment && !useCaseAssessment.is_supported && (
            <div className="unsupported-card">
              <h3>Outside supported use cases</h3>
              <p>Upload project scope notes, proposal docs, or requirements specifications.</p>
              {useCaseAssessment.reasons.length > 0 && (
                <ul className="unsupported-reasons">
                  {useCaseAssessment.reasons.map((r) => <li key={r}>{r}</li>)}
                </ul>
              )}
            </div>
          )}
        </article>

        {/* ════ RIGHT — Generate + Outputs ════ */}
        <div className="studio-right">

          {/* Generate panel */}
          <article className="card studio-generate">
            <header className="step-header">
              <span className="step-badge">02</span>
              <div>
                <h2>Generate Deliverables</h2>
                <p className="step-desc">
                  {parsedDocument ? `Using: ${parsedDocument.title}` : "Parse a document first"}
                </p>
              </div>
            </header>

            {/* Tabs */}
            <div className="gen-tabs">
              <button
                className={`gen-tab${activeTab === "sow" ? " active" : ""}`}
                type="button"
                onClick={() => setActiveTab("sow")}
              >
                <FileText size={14} /> SOW
              </button>
              <button
                className={`gen-tab${activeTab === "ppt" ? " active" : ""}`}
                type="button"
                onClick={() => setActiveTab("ppt")}
              >
                <Presentation size={14} /> Presentation
              </button>
              <button
                className={`gen-tab${activeTab === "summarize" ? " active" : ""}`}
                type="button"
                onClick={() => setActiveTab("summarize")}
              >
                <AlignLeft size={14} /> Summarize
              </button>
              <button
                className={`gen-tab${activeTab === "bid" ? " active" : ""}`}
                type="button"
                onClick={() => setActiveTab("bid")}
              >
                <FilePlus2 size={14} /> Bid Response
              </button>
            </div>

            {/* SOW tab */}
            {activeTab === "sow" && (
              <div className="gen-form">
                <label className="field-label">
                  Client name
                  <input
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    placeholder="e.g. Acme Corporation"
                  />
                </label>
                <label className="field-label">
                  Assumptions <span className="field-hint">(one per line)</span>
                  <textarea
                    rows={4}
                    value={assumptions}
                    onChange={(e) => setAssumptions(e.target.value)}
                    placeholder="e.g. Client will provide access to source systems…"
                  />
                </label>
                <button
                  className="btn btn-primary gen-btn"
                  type="button"
                  onClick={handleGenerateSow}
                  disabled={!parsedDocument || sowLoading}
                >
                  {sowLoading
                    ? <><Loader2 size={14} className="spin" /> Generating SOW…</>
                    : <><WandSparkles size={14} /> Generate SOW</>
                  }
                </button>
                {!parsedDocument && <p className="field-hint-block">Parse a document to enable generation.</p>}
              </div>
            )}

            {/* PPT tab */}
            {activeTab === "ppt" && (
              <div className="gen-form">
                <label className="field-label">
                  Deck title
                  <input
                    value={deckTitle}
                    onChange={(e) => setDeckTitle(e.target.value)}
                    placeholder="e.g. BSBI Document Intelligence Brief"
                  />
                </label>
                <label className="field-label">
                  Subtitle
                  <input
                    value={subtitle}
                    onChange={(e) => setSubtitle(e.target.value)}
                    placeholder="e.g. Generated from uploaded document"
                  />
                </label>
                <label className="field-label">
                  Max content slides
                  <input
                    type="number"
                    min={3}
                    max={12}
                    value={maxSlides}
                    onChange={(e) => {
                      const v = Number(e.target.value);
                      setMaxSlides(Number.isNaN(v) ? 6 : Math.min(12, Math.max(3, v)));
                    }}
                  />
                </label>
                <button
                  className="btn btn-primary gen-btn"
                  type="button"
                  onClick={handleGeneratePpt}
                  disabled={!parsedDocument || pptLoading}
                >
                  {pptLoading
                    ? <><Loader2 size={14} className="spin" /> Generating PPT…</>
                    : <><WandSparkles size={14} /> Generate Presentation</>
                  }
                </button>
                {!parsedDocument && <p className="field-hint-block">Parse a document to enable generation.</p>}
              </div>
            )}

            {/* Bid tab */}
            {activeTab === "bid" && (
              <div className="gen-form">
                <label className="field-label">
                  Client name
                  <input
                    value={clientName}
                    onChange={(e) => setClientName(e.target.value)}
                    placeholder="e.g. Acme Corporation"
                  />
                </label>
                <label className="field-label">
                  Opportunity / tender title
                  <input
                    value={bidOpportunityTitle}
                    onChange={(e) => setBidOpportunityTitle(e.target.value)}
                    placeholder="e.g. Digital Transformation Programme"
                  />
                </label>
                <label className="field-label">
                  Our key strengths <span className="field-hint">(one per line)</span>
                  <textarea
                    rows={4}
                    value={bidStrengths}
                    onChange={(e) => setBidStrengths(e.target.value)}
                    placeholder="e.g. 10 years nuclear sector experience&#10;Fixed-price delivery model&#10;Dedicated local team"
                  />
                </label>
                <button
                  className="btn btn-primary gen-btn"
                  type="button"
                  onClick={() => void handleGenerateBid()}
                  disabled={!parsedDocument || bidLoading}
                >
                  {bidLoading
                    ? <><Loader2 size={14} className="spin" /> Generating Bid…</>
                    : <><WandSparkles size={14} /> Generate Bid Response</>
                  }
                </button>
                {!parsedDocument && <p className="field-hint-block">Parse a document to enable generation.</p>}
              </div>
            )}

            {/* Summarize tab */}
            {activeTab === "summarize" && (
              <div className="gen-form">
                <div className="summary-mode-grid">
                  {SUMMARY_MODES.map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      className={`summary-mode-btn${summaryMode === m.id ? " active" : ""}`}
                      onClick={() => { setSummaryMode(m.id); setSummaryResult(null); setSummaryError(null); }}
                    >
                      <span className="summary-mode-label">{m.label}</span>
                      <span className="summary-mode-desc">{m.desc}</span>
                    </button>
                  ))}
                </div>

                {parsedDocument && (
                  <div className="summary-doc-context">
                    <span className="summary-context-pill">
                      {parsedDocument.extraction_signals?.[0]?.name.replaceAll("_", " ") ?? parsedDocument.file_type}
                    </span>
                    <span>· {parsedDocument.word_count} words · AI adapts tone to document type</span>
                  </div>
                )}

                <button
                  className="btn btn-primary gen-btn"
                  type="button"
                  onClick={handleSummarize}
                  disabled={!parsedDocument || summaryLoading}
                >
                  {summaryLoading
                    ? <><Loader2 size={14} className="spin" /> Summarizing…</>
                    : <><AlignLeft size={14} /> Generate Summary</>
                  }
                </button>
                {!parsedDocument && <p className="field-hint-block">Parse a document to enable summarization.</p>}

                {summaryError && (
                  <div className="message error">
                    <AlertCircle size={14} /><span>{summaryError}</span>
                  </div>
                )}

                {summaryResult && (
                  <div className="summary-result animate-fade-in" ref={summaryResultRef}>
                    <div className="summary-result-header">
                      <div>
                        <p className="summary-result-title">{summaryResult.title}</p>
                        {summaryResult.doc_context && (
                          <p className="summary-result-context">Detected as: {summaryResult.doc_context}</p>
                        )}
                      </div>
                      <button
                        className="btn-icon-copy"
                        type="button"
                        onClick={handleCopySummary}
                        title="Copy to clipboard"
                      >
                        {copied ? <ClipboardCheck size={14} /> : <Clipboard size={14} />}
                      </button>
                    </div>

                    {summaryResult.summary_line && (
                      <p className="summary-summary-line">{summaryResult.summary_line}</p>
                    )}

                    {summaryResult.paragraphs.map((p, i) => (
                      <p key={i} className="summary-paragraph">{p}</p>
                    ))}

                    {summaryResult.key_points.length > 0 && (
                      <ul className="summary-bullets">
                        {summaryResult.key_points.map((pt, i) => <li key={i}>{pt}</li>)}
                      </ul>
                    )}

                    {summaryResult.groups.map((g, i) => (
                      <div key={i} className="summary-group">
                        <p className="summary-group-heading">{g.heading}</p>
                        <ul className="summary-bullets">
                          {g.bullets.map((b, j) => <li key={j}>{b}</li>)}
                        </ul>
                      </div>
                    ))}

                    {summaryResult.insights.map((insight, i) => (
                      <div key={i} className={`summary-insight insight-${insight.significance}`}>
                        <span className="insight-sig">{insight.significance}</span>
                        <p>{insight.insight}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </article>

          {/* Outputs panel */}
          <article className="card studio-outputs">
            <header className="step-header">
              <span className="step-badge">03</span>
              <div>
                <h2>Session Outputs</h2>
                <p className="step-desc">Artifacts ready to download</p>
              </div>
              <div className="outputs-counters">
                <span className="output-counter">
                  <FileText size={11} /> {sowCount} SOW
                </span>
                <span className="output-counter">
                  <Presentation size={11} /> {pptCount} PPT
                </span>
                <span className="output-counter total">
                  <FilePlus2 size={11} /> {outputs.length}
                </span>
              </div>
            </header>

            {outputs.length === 0 ? (
              <div className="outputs-empty">
                <Download size={20} strokeWidth={1.5} />
                <p>Generated files will appear here</p>
              </div>
            ) : (
              <div className="outputs-list">
                {outputs.slice(0, 8).map((artifact) => (
                  <div key={artifact.id} className="output-row">
                    <span className={`output-type-badge ${artifact.artifact_type}`}>
                      {artifact.artifact_type.toUpperCase()}
                    </span>
                    <span className="output-name">{artifact.artifact_name}</span>
                    <button
                      className="btn-icon-download"
                      type="button"
                      title="Download"
                      onClick={() => handleDownload(artifact.download_url, artifact.artifact_name)}
                    >
                      <Download size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </article>
        </div>
      </div>
    </div>
  );
};

export default StudioView;