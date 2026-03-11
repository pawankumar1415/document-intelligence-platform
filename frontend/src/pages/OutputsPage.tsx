import { Download, FileStack } from "lucide-react";
import { useState } from "react";

import { useAppState } from "../context/AppStateContext";
import { downloadArtifact } from "../services/api";

const OutputsPage = () => {
  const { outputs, token } = useAppState();
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async (downloadUrl: string, artifactName: string) => {
    setError(null);
    try {
      await downloadArtifact(downloadUrl, artifactName, { token });
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Download failed.";
      setError(message);
    }
  };

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
              <button
                className="btn-primary"
                type="button"
                onClick={() => handleDownload(artifact.download_url, artifact.artifact_name)}
              >
                <Download size={16} /> Download
              </button>
            </article>
          ))}
        </div>
      )}
      {error && (
        <div className="message error">
          <span>{error}</span>
        </div>
      )}
    </section>
  );
};

export default OutputsPage;
