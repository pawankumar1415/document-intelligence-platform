import {
  AlertCircle,
  BookMarked,
  Check,
  Clock,
  Copy,
  Download,
  FileStack,
  FileText,
  Link2,
  Presentation,
  Share2,
  ThumbsDown,
  ThumbsUp,
  Trash2,
} from "lucide-react";
import { useState } from "react";

import { useAppState } from "../context/AppStateContext";
import {
  createShareLink,
  downloadArtifact,
  revokeShareLink,
  submitFeedback,
} from "../services/api";
import type { ShareLinkRecord } from "../types/app";

const TYPE_META = {
  sow:        { label: "SOW",        Icon: FileText,     color: "badge-sow" },
  pptx:       { label: "PPT",        Icon: Presentation, color: "badge-ppt" },
  bid:        { label: "Bid",        Icon: FileText,     color: "badge-sow" },
  case_study: { label: "Case Study", Icon: BookMarked,   color: "badge-sow" },
  register:   { label: "Register",   Icon: FileText,     color: "badge-sow" },
} as const;

type FeedbackState = Record<string, 1 | -1 | null>; // artifactId → rating

const OutputsView = () => {
  const { outputs, token } = useAppState();

  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  // Feedback
  const [feedback, setFeedback] = useState<FeedbackState>({});
  const [submittingFeedback, setSubmittingFeedback] = useState<string | null>(null);

  // Share links
  const [shareLinks, setShareLinks] = useState<Record<string, ShareLinkRecord>>({});
  const [sharingFor, setSharingFor] = useState<string | null>(null);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

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

  const handleFeedback = async (artifactId: number | undefined, key: string, rating: 1 | -1) => {
    if (!artifactId) return;
    if (feedback[key] === rating) return; // already set
    setSubmittingFeedback(key);
    try {
      await submitFeedback(artifactId, { rating, section_title: "", note: "" }, { token });
      setFeedback((prev) => ({ ...prev, [key]: rating }));
    } catch {
      // silently ignore
    } finally {
      setSubmittingFeedback(null);
    }
  };

  const handleShare = async (artifactId: number | undefined, key: string) => {
    if (!artifactId) return;
    setSharingFor(key);
    try {
      const link = await createShareLink(artifactId, {}, { token });
      setShareLinks((prev) => ({ ...prev, [key]: link }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create share link.");
    } finally {
      setSharingFor(null);
    }
  };

  const handleCopy = (token: string, key: string) => {
    const url = `${window.location.origin}/share/${token}`;
    navigator.clipboard.writeText(url).catch(() => {});
    setCopiedToken(key);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  const handleRevoke = async (shareToken: string, key: string) => {
    try {
      await revokeShareLink(shareToken, { token });
      setShareLinks((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    } catch {
      // silently ignore
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
            const meta = TYPE_META[artifact.artifact_type as keyof typeof TYPE_META] ?? TYPE_META.sow;
            const { Icon } = meta;
            const key = artifact.id;
            const artId = artifact.artifact_id;
            const currentRating = feedback[key];
            const shareLink = shareLinks[key];

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

                {/* Download */}
                <button
                  className="btn btn-primary library-download-btn"
                  type="button"
                  onClick={() => handleDownload(artifact.download_url, artifact.artifact_name)}
                  disabled={downloading === artifact.artifact_name}
                >
                  <Download size={14} />
                  {downloading === artifact.artifact_name ? "Downloading…" : "Download"}
                </button>

                {/* Feedback + Share row */}
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "8px" }}>
                  {/* Thumbs up/down */}
                  <button
                    type="button"
                    title="Good output"
                    onClick={() => handleFeedback(artId, key, 1)}
                    disabled={submittingFeedback === key}
                    style={{
                      background: currentRating === 1 ? "rgba(22,163,74,0.12)" : "transparent",
                      border: `1px solid ${currentRating === 1 ? "rgba(22,163,74,0.4)" : "var(--border-color)"}`,
                      borderRadius: "6px", padding: "5px 8px", cursor: "pointer",
                      color: currentRating === 1 ? "#16a34a" : "var(--text-muted)",
                      display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem",
                    }}
                  >
                    <ThumbsUp size={13} />
                  </button>
                  <button
                    type="button"
                    title="Needs improvement"
                    onClick={() => handleFeedback(artId, key, -1)}
                    disabled={submittingFeedback === key}
                    style={{
                      background: currentRating === -1 ? "rgba(220,38,38,0.10)" : "transparent",
                      border: `1px solid ${currentRating === -1 ? "rgba(220,38,38,0.35)" : "var(--border-color)"}`,
                      borderRadius: "6px", padding: "5px 8px", cursor: "pointer",
                      color: currentRating === -1 ? "#dc2626" : "var(--text-muted)",
                      display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem",
                    }}
                  >
                    <ThumbsDown size={13} />
                  </button>

                  <div style={{ flex: 1 }} />

                  {/* Share button — only if artifact has a DB id */}
                  {artId && !shareLink && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      title="Create share link"
                      onClick={() => handleShare(artId, key)}
                      disabled={sharingFor === key}
                      style={{ padding: "5px 10px", fontSize: "0.78rem", display: "flex", alignItems: "center", gap: "4px" }}
                    >
                      <Share2 size={13} />
                      {sharingFor === key ? "…" : "Share"}
                    </button>
                  )}
                </div>

                {/* Share link panel */}
                {shareLink && (
                  <div style={{
                    marginTop: "8px", padding: "10px 12px",
                    background: "rgba(79,70,229,0.06)", border: "1px solid rgba(79,70,229,0.18)",
                    borderRadius: "8px", display: "flex", flexDirection: "column", gap: "6px",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.77rem", color: "#4f46e5" }}>
                      <Link2 size={12} />
                      <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        /share/{shareLink.token.slice(0, 20)}…
                      </span>
                      <button
                        type="button"
                        title="Copy link"
                        onClick={() => handleCopy(shareLink.token, key)}
                        style={{ background: "none", border: "none", cursor: "pointer", color: "#4f46e5", padding: "2px 4px", display: "flex", alignItems: "center" }}
                      >
                        {copiedToken === key ? <Check size={13} /> : <Copy size={13} />}
                      </button>
                      <button
                        type="button"
                        title="Revoke link"
                        onClick={() => handleRevoke(shareLink.token, key)}
                        style={{ background: "none", border: "none", cursor: "pointer", color: "#dc2626", padding: "2px 4px", display: "flex", alignItems: "center" }}
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                    {shareLink.expires_at && (
                      <div style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                        Expires {new Date(shareLink.expires_at).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default OutputsView;