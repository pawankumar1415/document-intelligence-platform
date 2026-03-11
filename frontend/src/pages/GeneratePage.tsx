import { AlertCircle, CheckCircle2, FileText, Loader2, Presentation } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useAppState } from "../context/AppStateContext";
import { generatePptx, generateSow } from "../services/api";

const GeneratePage = () => {
  const { parsedDocument, addOutput } = useAppState();

  const [clientName, setClientName] = useState("BSBI Consulting");
  const [projectName, setProjectName] = useState("Document Intelligence Discovery");
  const [assumptions, setAssumptions] = useState("");
  const [deckTitle, setDeckTitle] = useState("BSBI Document Intelligence Brief");
  const [subtitle, setSubtitle] = useState("Generated from uploaded document");
  const [maxSlides, setMaxSlides] = useState(4);

  const [loadingSow, setLoadingSow] = useState(false);
  const [loadingPpt, setLoadingPpt] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!parsedDocument) {
    return (
      <section className="page">
        <div className="panel empty-state">
          <AlertCircle size={24} />
          <h2>No parsed document available</h2>
          <p>Upload and parse a `.docx` or `.txt` file first.</p>
          <Link className="btn-primary" to="/upload">
            Go To Upload
          </Link>
        </div>
      </section>
    );
  }

  const handleSowGenerate = async () => {
    setLoadingSow(true);
    setMessage(null);
    setError(null);
    try {
      const response = await generateSow({
        client_name: clientName,
        project_name: projectName,
        source_document: {
          title: parsedDocument.title,
          text: parsedDocument.text,
          sections: parsedDocument.sections,
        },
        assumptions: assumptions
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean),
      });
      addOutput(response);
      setMessage("SOW draft generated successfully.");
    } catch (requestError) {
      const msg = requestError instanceof Error ? requestError.message : "Failed to generate SOW.";
      setError(msg);
    } finally {
      setLoadingSow(false);
    }
  };

  const handlePptGenerate = async () => {
    setLoadingPpt(true);
    setMessage(null);
    setError(null);
    try {
      const response = await generatePptx({
        deck_title: deckTitle,
        subtitle,
        source_document: {
          title: parsedDocument.title,
          text: parsedDocument.text,
          sections: parsedDocument.sections,
        },
        max_content_slides: maxSlides,
      });
      addOutput(response);
      setMessage("Presentation draft generated successfully.");
    } catch (requestError) {
      const msg = requestError instanceof Error ? requestError.message : "Failed to generate PPT.";
      setError(msg);
    } finally {
      setLoadingPpt(false);
    }
  };

  return (
    <section className="page">
      <div className="section-header">
        <h1>Generate Deliverables</h1>
        <p>Use the parsed content to create draft SOW and PPT outputs.</p>
      </div>

      {message && (
        <div className="message success">
          <CheckCircle2 size={16} />
          <span>{message}</span>
        </div>
      )}
      {error && (
        <div className="message error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div className="generate-grid">
        <article className="panel">
          <h2>
            <FileText size={18} /> SOW Draft
          </h2>
          <label>
            Client name
            <input value={clientName} onChange={(event) => setClientName(event.target.value)} />
          </label>
          <label>
            Project name
            <input value={projectName} onChange={(event) => setProjectName(event.target.value)} />
          </label>
          <label>
            Assumptions (one per line)
            <textarea
              rows={4}
              value={assumptions}
              onChange={(event) => setAssumptions(event.target.value)}
            />
          </label>
          <button className="btn-primary" type="button" disabled={loadingSow} onClick={handleSowGenerate}>
            {loadingSow ? (
              <>
                <Loader2 size={16} className="spin" /> Generating...
              </>
            ) : (
              "Generate SOW"
            )}
          </button>
        </article>

        <article className="panel">
          <h2>
            <Presentation size={18} /> Presentation Draft
          </h2>
          <label>
            Deck title
            <input value={deckTitle} onChange={(event) => setDeckTitle(event.target.value)} />
          </label>
          <label>
            Subtitle
            <input value={subtitle} onChange={(event) => setSubtitle(event.target.value)} />
          </label>
          <label>
            Max content slides
            <input
              type="number"
              min={2}
              max={8}
              value={maxSlides}
              onChange={(event) => {
                const value = Number(event.target.value);
                if (Number.isNaN(value)) {
                  setMaxSlides(4);
                  return;
                }
                setMaxSlides(Math.min(8, Math.max(2, value)));
              }}
            />
          </label>
          <button className="btn-primary" type="button" disabled={loadingPpt} onClick={handlePptGenerate}>
            {loadingPpt ? (
              <>
                <Loader2 size={16} className="spin" /> Generating...
              </>
            ) : (
              "Generate PPT"
            )}
          </button>
        </article>
      </div>
    </section>
  );
};

export default GeneratePage;
