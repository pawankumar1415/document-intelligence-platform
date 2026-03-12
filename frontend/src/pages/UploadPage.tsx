import { AlertCircle, CheckCircle2, Loader2, UploadCloud } from "lucide-react";
import { useState } from "react";

import { useAppState } from "../context/AppStateContext";
import { ApiError, parseDocument } from "../services/api";
import type { UseCaseAssessment } from "../types/app";

const UploadPage = () => {
  const { parsedDocument, projectId, setParsedDocument, setProjectId, token, llmProvider } = useAppState();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [projectName, setProjectName] = useState("BSBI Discovery Project");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [useCaseAssessment, setUseCaseAssessment] = useState<UseCaseAssessment | null>(null);

  const handleParse = async () => {
    if (!selectedFile) {
      setError("Select a .docx or .txt file before parsing.");
      return;
    }

    setLoading(true);
    setError(null);
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
    } catch (requestError) {
      if (requestError instanceof ApiError) {
        if (requestError.status === 422 && requestError.payload?.code === "unsupported_document") {
          setError(
            requestError.payload.message ||
              "This document does not fit the currently supported use cases for this product.",
          );
          setUseCaseAssessment(requestError.payload.assessment ?? null);
          setParsedDocument(null);
          return;
        }
        setError(requestError.message || "Failed to parse document.");
        setUseCaseAssessment(null);
      } else {
        const message =
          requestError instanceof Error ? requestError.message : "Failed to parse document.";
        setError(message);
        setUseCaseAssessment(null);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="page">
      <div className="section-header">
        <h1>Upload Source Document</h1>
        <p>Supported now: `.docx` and `.txt`. Parse once, then generate multiple outputs.</p>
      </div>

      <div className="panel">
        <label>
          Project name
          <input value={projectName} onChange={(event) => setProjectName(event.target.value)} />
        </label>
        <label className="file-drop">
          <UploadCloud size={24} />
          <div>
            <strong>Choose document</strong>
            <p>Drop file here or click to browse.</p>
          </div>
          <input
            type="file"
            accept=".docx,.txt"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
        </label>

        <div className="inline-meta">
          <span>{selectedFile ? selectedFile.name : "No file selected"}</span>
          <button className="btn-primary" type="button" onClick={handleParse} disabled={loading}>
            {loading ? (
              <>
                <Loader2 size={16} className="spin" /> Parsing...
              </>
            ) : (
              "Parse Document"
            )}
          </button>
        </div>

        {error && (
          <div className="message error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
        {useCaseAssessment && !useCaseAssessment.is_supported && (
          <div className="unsupported-card">
            <h3>This file is outside current supported use cases</h3>
            <p>
              The platform currently supports documents for SOW generation, presentation generation, and
              requirement extraction.
            </p>
            {!!useCaseAssessment.reasons.length && (
              <ul className="unsupported-reasons">
                {useCaseAssessment.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
            <p className="unsupported-hint">
              Try uploading project scope notes, proposal documents, requirement specs, or business planning
              documents.
            </p>
          </div>
        )}
        {parsedDocument && (
          <div className="message success">
            <CheckCircle2 size={16} />
            <span>Parsed successfully: {parsedDocument.filename}</span>
          </div>
        )}
      </div>

      {parsedDocument && (
        <div className="panel">
          <h2>Parsed Summary</h2>
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
              <small>Paragraphs</small>
              <p>{parsedDocument.paragraph_count}</p>
            </div>
          </div>

          <h3>Detected Sections</h3>
          <div className="section-list">
            {parsedDocument.sections.slice(0, 8).map((section) => (
              <article key={`${section.heading}-${section.body.slice(0, 24)}`} className="section-card">
                <h4>{section.heading}</h4>
                <p>{section.body}</p>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
};

export default UploadPage;
