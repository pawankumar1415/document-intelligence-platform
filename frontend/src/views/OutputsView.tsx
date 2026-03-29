import { AlertCircle, Clock, Download, FileStack, FileText, Presentation } from "lucide-react";
import { useState } from "react";

import { useAppState } from "../context/AppStateContext";
import { downloadArtifact } from "../services/api";

const TYPE_META = {
  sow:  { label: "SOW", Icon: FileText,     color: "badge-sow" },
  pptx: { label: "PPT", Icon: Presentation, color: "badge-ppt" },
} as const;

const OutputsView = () => {
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

  const sowCount  = outputs.filter((o) => o.artifact_type === "sow").length;
  const pptCount  = outputs.filter((o) => o.artifact_type === "pptx").length;

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <h1 className="page-title">Output Library</h1>
          <p className="page-subtitle">
            {outputs.length === 0
              ? "Generated files will appear here after running SOW or PPT generation."
              : `${outputs.length} artifact${outputs.length !== 1 ? "s" : ""} generated this session`}
          </p>
        </div>
        {outputs.length > 0 && (
          <div style={{ display: "flex", gap: "8px", flexShrink: 0 }}>
            <span style={{
              display: "flex", alignItems: "center", gap: "5px",
              background: "rgba(211,47,47,0.08)", color: "var(--bsbi-red)",
              border: "1px solid rgba(211,47,47,0.18)", borderRadius: "20px",
              padding: "4px 12px", fontSize: "0.78rem", fontWeight: 600,
            }}>
              <FileText size={13} /> {sowCount} SOW
            </span>
            <span style={{
              display: "flex", alignItems: "center", gap: "5px",
              background: "rgba(79,70,229,0.08)", color: "#4f46e5",
              border: "1px solid rgba(79,70,229,0.18)", borderRadius: "20px",
              padding: "4px 12px", fontSize: "0.78rem", fontWeight: 600,
            }}>
              <Presentation size={13} /> {pptCount} PPT
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="message error">
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {outputs.length === 0 ? (
        <div className="card library-empty">
          <FileStack size={38} strokeWidth={1.3} />
          <h2>No outputs yet</h2>
          <p>Head to Studio, upload a document, and generate your first deliverable.</p>
        </div>
      ) : (
        <div className="library-grid">
          {outputs.map((artifact) => {
            const meta = TYPE_META[artifact.artifact_type] ?? TYPE_META.sow;
            const { Icon } = meta;
            return (
              <article key={artifact.id} className="card library-card">
                <div className="library-card-top">
                  <div className={`library-card-icon ${meta.color}`}>
                    <Icon size={18} />
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
                  className="btn btn-primary library-download-btn"
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
    </div>
  );
};

export default OutputsView;