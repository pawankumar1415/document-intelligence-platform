import { FileCheck2, FilePlus2, FileText, Presentation } from "lucide-react";
import { Link } from "react-router-dom";

import { useAppState } from "../context/AppStateContext";

const DashboardPage = () => {
  const { parsedDocument, outputs, llmProvider } = useAppState();

  const sowCount = outputs.filter((item) => item.artifact_type === "sow").length;
  const pptCount = outputs.filter((item) => item.artifact_type === "pptx").length;

  return (
    <section className="page">
      <div className="hero">
        <p className="eyebrow">BSBI Consulting Workflow</p>
        <h1>Document-to-Deliverable in Four Steps</h1>
        <p>
          Upload a `.txt`, `.docx`, or `.pdf`, extract structure, generate a draft SOW or PPT, and
          download stakeholder-ready files.
        </p>
        <p style={{ marginTop: "0.35rem", fontSize: "0.86rem" }}>
          Current LLM Provider: <strong>{llmProvider}</strong>
        </p>
        <div className="hero-actions">
          <Link className="btn-primary" to="/upload">
            Start With Upload
          </Link>
          <Link className="btn-ghost" to="/generate">
            Go To Generation
          </Link>
        </div>
      </div>

      <div className="stats-grid">
        <article className="stat-card">
          <FileCheck2 size={18} />
          <h3>Parsed Document</h3>
          <p>{parsedDocument ? parsedDocument.filename : "No document parsed yet"}</p>
        </article>
        <article className="stat-card">
          <FileText size={18} />
          <h3>SOW Drafts</h3>
          <p>{sowCount}</p>
        </article>
        <article className="stat-card">
          <Presentation size={18} />
          <h3>PPT Drafts</h3>
          <p>{pptCount}</p>
        </article>
        <article className="stat-card">
          <FilePlus2 size={18} />
          <h3>Total Outputs</h3>
          <p>{outputs.length}</p>
        </article>
      </div>

      <div className="panel">
        <h2>How this demo works</h2>
        <ol className="ordered-list">
          <li>Upload one source document and parse it into structured sections.</li>
          <li>Generate a draft SOW or presentation deck from the extracted content.</li>
          <li>Track generated artifacts in the Outputs screen.</li>
          <li>Download `.docx` and `.pptx` files through backend file endpoints.</li>
        </ol>
      </div>
    </section>
  );
};

export default DashboardPage;
