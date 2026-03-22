import { AlertCircle, Clock, Download, FileStack, FileText, Presentation } from "lucide-react";
import { useState } from "react";

import { useAppState } from "../context/AppStateContext";
import { downloadArtifact } from "../services/api";

const TYPE_META = {
  sow: { label: "SOW", Icon: FileText, color: "badge-sow" },
  pptx: { label: "PPT", Icon: Presentation, color: "badge-ppt" },
} as const;

const OutputsPage = () => {
  const { outputs, token } = useAppState();
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleDownload = async (downloadUrl: string, artifactName: string) => {
    setError(null);
    setDownloading(artifactName);
    try {
      await downloadArtifact(downloadUrl, artifactName, { token });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed.");
    } finally {
      setDownloading(null);
    }
  };

  return (
    <section className="page">
      <div className="library-header">
        <div>
          <p className="eyebrow">Session Artifacts</p>
          <h1 className="library-title">Output Library</h1>
          <p className="library-subtitle">
            {outputs.length === 0
              ? "Generated files will appear here after running SOW or PPT generation."
              : `${outputs.length} artifact${outputs.length !== 1 ? "s" : ""} generated this session`}
          </p>
        </div>
        <div className="library-counts">
          <div className="library-count-pill">
            <FileText size={14} />
            <span>{outputs.filter((o) => o.artifact_type === "sow").length} SOW</span>
          </div>
          <div className="library-count-pill">
            <Presentation size={14} />
            <span>{outputs.filter((o) => o.artifact_type === "pptx").length} PPT</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="message error">
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {outputs.length === 0 ? (
        <div className="library-empty panel">
          <FileStack size={40} strokeWidth={1.2} />
          <h2>No outputs yet</h2>
          <p>Head to Studio, upload a document, and generate your first deliverable.</p>
        </div>
      ) : (
        <div className="library-grid">
          {outputs.map((artifact) => {
            const meta = TYPE_META[artifact.artifact_type] ?? TYPE_META.sow;
            const { Icon } = meta;
            return (
              <article key={artifact.id} className="library-card panel">
                <div className="library-card-top">
                  <div className={`library-card-icon ${meta.color}`}>
                    <Icon size={20} />
                  </div>
                  <span className={`artifact-type-badge ${meta.color}`}>{meta.label}</span>
                </div>

                <h3 className="library-card-title">{artifact.summary || artifact.artifact_name}</h3>

                <div className="library-card-meta">
                  <span>
                    <Clock size={11} />
                    {new Date(artifact.created_at).toLocaleString(undefined, {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </span>
                  <span className="library-card-filename">{artifact.artifact_name}</span>
                </div>

                <button
                  className="btn-primary library-download-btn"
                  type="button"
                  onClick={() => handleDownload(artifact.download_url, artifact.artifact_name)}
                  disabled={downloading === artifact.artifact_name}
                >
                  <Download size={14} />
                  {downloading === artifact.artifact_name ? "Downloading…" : "Download"}
                </button>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
};

export default OutputsPage;