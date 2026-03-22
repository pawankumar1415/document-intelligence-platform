import {
  AlertCircle,
  CheckCircle2,
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
import { useState } from "react";

import { useAppState } from "../context/AppStateContext";
import { ApiError, downloadArtifact, generatePptx, generateSow, parseDocument } from "../services/api";
import type { UseCaseAssessment } from "../types/app";

type GenTab = "sow" | "ppt";

const DashboardPage = () => {
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
  const [parseError, setParseError] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [useCaseAssessment, setUseCaseAssessment] = useState<UseCaseAssessment | null>(null);

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
      setStatusMessage(`"${response.document.title}" parsed — ${response.document.word_count} words, ${response.document.sections.length} sections.`);
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
      setGenerateError(err instanceof Error ? err.message : "Could not generate PPT.");
    } finally {
      setPptLoading(false);
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

  const anyError = parseError || generateError || downloadError;

  return (
    <section className="page">
      {/* ── Status bar ── */}
      <div className="studio-bar">
        <div className="studio-bar-doc">
          {parsedDocument ? (
            <>
              <FileCheck2 size={14} className="studio-bar-icon ok" />
              <span className="studio-bar-label">
                <strong>{parsedDocument.title}</strong>
                <span className="studio-bar-meta">{parsedDocument.file_type?.toUpperCase()} · {parsedDocument.word_count} words · {parsedDocument.sections.length} sections</span>
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
          {llmModel && <><span className="studio-bar-sep">·</span><span className="studio-bar-model">{llmModel}</span></>}
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
        <article className="panel studio-doc">
          <header className="step-header">
            <span className="step-badge">01</span>
            <div>
              <h2>Source Document</h2>
              <p className="step-desc">Upload a project brief, proposal, or requirements doc</p>
            </div>
          </header>

          <label className="field-label">
            Project name
            <input value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder="e.g. BSBI Discovery Project" />
          </label>

          {!parsedDocument ? (
            <>
              <label className="dropzone">
                <input
                  type="file"
                  accept=".docx,.txt,.pdf"
                  onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
                />
                <UploadCloud size={36} strokeWidth={1.5} className="dropzone-icon" />
                <strong>Drop file here or click to browse</strong>
                <span>.docx · .txt · .pdf supported</span>
              </label>

              {selectedFile && (
                <div className="selected-file-row">
                  <span className="selected-file-name">
                    <FileText size={14} />
                    {selectedFile.name}
                  </span>
                  <button className="btn-primary" type="button" onClick={handleParse} disabled={parseLoading}>
                    {parseLoading ? <><Loader2 size={14} className="spin" /> Parsing…</> : "Parse Document"}
                  </button>
                </div>
              )}

              {!selectedFile && (
                <p className="dropzone-hint">Select a file above, then click Parse to extract content.</p>
              )}
            </>
          ) : (
            <>
              <div className="doc-loaded-card">
                <div className="doc-loaded-icon">
                  <FileCheck2 size={22} />
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
                    <span key={s.name} className="signal-chip">{s.name.replaceAll("_", " ")}</span>
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
          <article className="panel studio-generate">
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
                <FileText size={14} /> Statement of Work
              </button>
              <button
                className={`gen-tab${activeTab === "ppt" ? " active" : ""}`}
                type="button"
                onClick={() => setActiveTab("ppt")}
              >
                <Presentation size={14} /> Presentation
              </button>
            </div>

            {activeTab === "sow" ? (
              <div className="gen-form">
                <label className="field-label">
                  Client name
                  <input value={clientName} onChange={(e) => setClientName(e.target.value)} placeholder="e.g. Acme Corporation" />
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
                  className="btn-primary gen-btn"
                  type="button"
                  onClick={handleGenerateSow}
                  disabled={!parsedDocument || sowLoading}
                >
                  {sowLoading ? <><Loader2 size={15} className="spin" /> Generating SOW…</> : <><WandSparkles size={15} /> Generate SOW</>}
                </button>
                {!parsedDocument && <p className="field-hint-block">Parse a document to enable generation.</p>}
              </div>
            ) : (
              <div className="gen-form">
                <label className="field-label">
                  Deck title
                  <input value={deckTitle} onChange={(e) => setDeckTitle(e.target.value)} placeholder="e.g. BSBI Document Intelligence Brief" />
                </label>
                <label className="field-label">
                  Subtitle
                  <input value={subtitle} onChange={(e) => setSubtitle(e.target.value)} placeholder="e.g. Generated from uploaded document" />
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
                  className="btn-primary gen-btn"
                  type="button"
                  onClick={handleGeneratePpt}
                  disabled={!parsedDocument || pptLoading}
                >
                  {pptLoading ? <><Loader2 size={15} className="spin" /> Generating PPT…</> : <><WandSparkles size={15} /> Generate Presentation</>}
                </button>
                {!parsedDocument && <p className="field-hint-block">Parse a document to enable generation.</p>}
              </div>
            )}
          </article>

          {/* Outputs panel */}
          <article className="panel studio-outputs">
            <header className="step-header">
              <span className="step-badge">03</span>
              <div>
                <h2>Outputs</h2>
                <p className="step-desc">Session artifacts ready to download</p>
              </div>
              <div className="outputs-counters">
                <span className="output-counter">
                  <FileText size={12} /> {sowCount} SOW
                </span>
                <span className="output-counter">
                  <Presentation size={12} /> {pptCount} PPT
                </span>
                <span className="output-counter total">
                  <FilePlus2 size={12} /> {outputs.length}
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
                      <Download size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </article>
        </div>
      </div>
    </section>
  );
};

export default DashboardPage;