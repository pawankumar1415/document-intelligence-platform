import { AlertCircle, CheckCircle2, Loader2, UploadCloud } from "lucide-react";
import { useState } from "react";

import { useAppState } from "../context/AppStateContext";
import { parseDocument } from "../services/api";

const UploadPage = () => {
  const { parsedDocument, setParsedDocument } = useAppState();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleParse = async () => {
    if (!selectedFile) {
      setError("Select a .docx or .txt file before parsing.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await parseDocument(selectedFile);
      setParsedDocument(response.document);
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "Failed to parse document.";
      setError(message);
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
