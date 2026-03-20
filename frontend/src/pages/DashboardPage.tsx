import {
  AlertCircle,
  CheckCircle2,
  Download,
  FileCheck2,
  FilePlus2,
  FileText,
  Loader2,
  Presentation,
  UploadCloud,
  WandSparkles,
} from "lucide-react";
import { useState } from "react";

import { useAppState } from "../context/AppStateContext";
import { ApiError, downloadArtifact, generatePptx, generateSow, parseDocument } from "../services/api";
import type { UseCaseAssessment } from "../types/app";

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

  const [parseLoading, setParseLoading] = useState(false);
  const [sowLoading, setSowLoading] = useState(false);
  const [pptLoading, setPptLoading] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [useCaseAssessment, setUseCaseAssessment] = useState<UseCaseAssessment | null>(null);

  const sowCount = outputs.filter((item) => item.artifact_type === "sow").length;
  const pptCount = outputs.filter((item) => item.artifact_type === "pptx").length;

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
      if (typeof response.project_id === "number") {
        setProjectId(response.project_id);
      }
      setUseCaseAssessment(response.use_case_assessment ?? null);
      setStatusMessage("Document parsed. You can generate SOW and PPT from this page.");
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        if (requestError.status === 422 && requestError.payload?.code === "unsupported_document") {
          setParseError(
            requestError.payload.message ||
              "This document does not match the currently supported generation use cases.",
          );
          setUseCaseAssessment(requestError.payload.assessment ?? null);
          setParsedDocument(null);
        } else {
          setParseError(requestError.message || "Could not parse the uploaded document.");
        }
      } else {
        const message = requestError instanceof Error ? requestError.message : "Could not parse the uploaded document.";
        setParseError(message);
      }
    } finally {
      setParseLoading(false);
    }
  };

  const handleGenerateSow = async () => {
    if (!parsedDocument) {
      setGenerateError("Parse a document before generating outputs.");
      return;
    }
    setSowLoading(true);
    setGenerateError(null);
    setStatusMessage(null);
    try {
      const response = await generateSow(
        {
          client_name: clientName,
          project_name: projectName,
          source_document: {
            title: parsedDocument.title,
            text: parsedDocument.text,
            sections: parsedDocument.sections,
          },
          project_id: projectId ?? undefined,
          llm_provider: llmProvider,
          llm_model: llmModel || undefined,
          assumptions: assumptions
            .split("\n")
            .map((line) => line.trim())
            .filter(Boolean),
        },
        { token },
      );
      addOutput(response);
      setStatusMessage("SOW generated successfully.");
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Could not generate SOW.";
      setGenerateError(message);
    } finally {
      setSowLoading(false);
    }
  };

  const handleGeneratePpt = async () => {
    if (!parsedDocument) {
      setGenerateError("Parse a document before generating outputs.");
      return;
    }
    setPptLoading(true);
    setGenerateError(null);
    setStatusMessage(null);
    try {
      const response = await generatePptx(
        {
          deck_title: deckTitle,
          subtitle,
          source_document: {
            title: parsedDocument.title,
            text: parsedDocument.text,
            sections: parsedDocument.sections,
          },
          project_id: projectId ?? undefined,
          llm_provider: llmProvider,
          llm_model: llmModel || undefined,
          max_content_slides: maxSlides,
        },
        { token },
      );
      addOutput(response);
      setStatusMessage("PPT generated successfully.");
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Could not generate PPT.";
      setGenerateError(message);
    } finally {
      setPptLoading(false);
    }
  };

  const handleDownload = async (downloadUrl: string, artifactName: string) => {
    setDownloadError(null);
    try {
      await downloadArtifact(downloadUrl, artifactName, { token });
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Download failed.";
      setDownloadError(message);
    }
  };

  return (
    <section className="page">
      <div className="hero">
        <p className="eyebrow">BSBI Studio Workflow</p>
        <h1>Upload, Parse, Generate, and Download From One Screen</h1>
        <p>No route-hopping. Complete the full document-to-deliverable flow in this studio view.</p>
        <p style={{ marginTop: "0.35rem", fontSize: "0.86rem" }}>
          Runtime: <strong>{llmProvider}</strong>
          {llmModel ? (
            <>
              {" "}
              / <strong>{llmModel}</strong>
            </>
          ) : null}
        </p>
      </div>

      {statusMessage && (
        <div className="message success">
          <CheckCircle2 size={16} />
          <span>{statusMessage}</span>
        </div>
      )}
      {(parseError || generateError || downloadError) && (
        <div className="message error">
          <AlertCircle size={16} />
          <span>{parseError || generateError || downloadError}</span>
        </div>
      )}

      <div className="workflow-grid">
        <article className="panel workflow-card">
          <div className="workflow-card-head">
            <span className="workflow-step">Step 01</span>
            <h2>
              <UploadCloud size={18} /> Upload and Parse
            </h2>
          </div>
          <label>
            Project name
            <input value={projectName} onChange={(event) => setProjectName(event.target.value)} />
          </label>
          <label className="file-drop">
            <UploadCloud size={24} />
            <div>
              <strong>Choose source document</strong>
              <p>Supported: `.docx`, `.txt`, `.pdf`.</p>
            </div>
            <input
              type="file"
              accept=".docx,.txt,.pdf"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <div className="inline-meta">
            <span>{selectedFile ? selectedFile.name : "No file selected"}</span>
            <button className="btn-primary" type="button" onClick={handleParse} disabled={parseLoading}>
              {parseLoading ? (
                <>
                  <Loader2 size={16} className="spin" /> Parsing...
                </>
              ) : (
                "Parse Document"
              )}
            </button>
          </div>

          {useCaseAssessment && !useCaseAssessment.is_supported && (
            <div className="unsupported-card">
              <h3>Unsupported use case for current scope</h3>
              <p>The platform currently supports SOW, presentation, and requirement-oriented documents.</p>
              {useCaseAssessment.reasons.length > 0 && (
                <ul className="unsupported-reasons">
                  {useCaseAssessment.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {parsedDocument && (
            <div className="summary-grid">
              <div>
                <small>Title</small>
                <p>{parsedDocument.title}</p>
              </div>
              <div>
                <small>Type</small>
                <p>{parsedDocument.file_type}</p>
              </div>
              <div>
                <small>Words</small>
                <p>{parsedDocument.word_count}</p>
              </div>
              <div>
                <small>Sections</small>
                <p>{parsedDocument.sections.length}</p>
              </div>
            </div>
          )}
        </article>

        <article className="panel workflow-card">
          <div className="workflow-card-head">
            <span className="workflow-step">Step 02</span>
            <h2>
              <WandSparkles size={18} /> Generate Deliverables
            </h2>
          </div>
          <label>
            Client name
            <input value={clientName} onChange={(event) => setClientName(event.target.value)} />
          </label>
          <label>
            Deck title
            <input value={deckTitle} onChange={(event) => setDeckTitle(event.target.value)} />
          </label>
          <label>
            Deck subtitle
            <input value={subtitle} onChange={(event) => setSubtitle(event.target.value)} />
          </label>
          <label>
            Max content slides
            <input
              type="number"
              min={3}
              max={12}
              value={maxSlides}
              onChange={(event) => {
                const value = Number(event.target.value);
                if (Number.isNaN(value)) {
                  setMaxSlides(6);
                  return;
                }
                setMaxSlides(Math.min(12, Math.max(3, value)));
              }}
            />
          </label>
          <label>
            Assumptions (one per line)
            <textarea rows={5} value={assumptions} onChange={(event) => setAssumptions(event.target.value)} />
          </label>
          <div className="hero-actions">
            <button className="btn-primary" type="button" onClick={handleGenerateSow} disabled={!parsedDocument || sowLoading}>
              {sowLoading ? (
                <>
                  <Loader2 size={16} className="spin" /> Generating SOW...
                </>
              ) : (
                "Generate SOW"
              )}
            </button>
            <button className="btn-primary" type="button" onClick={handleGeneratePpt} disabled={!parsedDocument || pptLoading}>
              {pptLoading ? (
                <>
                  <Loader2 size={16} className="spin" /> Generating PPT...
                </>
              ) : (
                "Generate PPT"
              )}
            </button>
          </div>
          {!parsedDocument && (
            <p className="model-control-note">Parse a document first to enable generation.</p>
          )}
        </article>

        <article className="panel workflow-card">
          <div className="workflow-card-head">
            <span className="workflow-step">Step 03</span>
            <h2>
              <Download size={18} /> Outputs
            </h2>
          </div>
          <div className="stats-grid workflow-stats">
            <article className="stat-card">
              <FileCheck2 size={18} />
              <h3>Parsed</h3>
              <p>{parsedDocument ? "Yes" : "No"}</p>
            </article>
            <article className="stat-card">
              <FileText size={18} />
              <h3>SOW</h3>
              <p>{sowCount}</p>
            </article>
            <article className="stat-card">
              <Presentation size={18} />
              <h3>PPT</h3>
              <p>{pptCount}</p>
            </article>
            <article className="stat-card">
              <FilePlus2 size={18} />
              <h3>Total</h3>
              <p>{outputs.length}</p>
            </article>
          </div>

          {outputs.length === 0 ? (
            <p className="model-control-note">No artifacts yet. Generate SOW or PPT above.</p>
          ) : (
            <div className="workflow-output-list">
              {outputs.slice(0, 6).map((artifact) => (
                <div key={artifact.id} className="workflow-output-item">
                  <div>
                    <p className="meta-line">{artifact.artifact_type.toUpperCase()}</p>
                    <p>{artifact.artifact_name}</p>
                  </div>
                  <button
                    className="btn-ghost"
                    type="button"
                    onClick={() => handleDownload(artifact.download_url, artifact.artifact_name)}
                  >
                    <Download size={14} /> Download
                  </button>
                </div>
              ))}
            </div>
          )}
        </article>
      </div>
    </section>
  );
};

export default DashboardPage;
