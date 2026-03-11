import { Download, FileStack } from "lucide-react";

import { useAppState } from "../context/AppStateContext";
import { downloadArtifactUrl } from "../services/api";

const OutputsPage = () => {
  const { outputs } = useAppState();

  return (
    <section className="page">
      <div className="section-header">
        <h1>Generated Outputs</h1>
        <p>Track generated artifacts and download editable files.</p>
      </div>

      {outputs.length === 0 ? (
        <div className="panel empty-state">
          <FileStack size={24} />
          <h2>No outputs generated yet</h2>
          <p>Run SOW or PPT generation to populate this list.</p>
        </div>
      ) : (
        <div className="outputs-grid">
          {outputs.map((artifact) => (
            <article key={artifact.id} className="panel output-card">
              <span className="artifact-tag">{artifact.artifact_type.toUpperCase()}</span>
              <h3>{artifact.summary}</h3>
              <p className="meta-line">Artifact: {artifact.artifact_name}</p>
              <p className="meta-line">
                Created: {new Date(artifact.created_at).toLocaleString()}
              </p>
              <a
                className="btn-primary"
                href={downloadArtifactUrl(artifact.download_url)}
                target="_blank"
                rel="noreferrer"
              >
                <Download size={16} /> Download
              </a>
            </article>
          ))}
        </div>
      )}
    </section>
  );
};

export default OutputsPage;
