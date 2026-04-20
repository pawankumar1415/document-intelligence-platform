import { AlertCircle, BookMarked, Download, ExternalLink, FileText, Layers, Presentation } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { downloadArtifactUrl, getSharedArtifact } from "../services/api";
import type { ShareLinkRecord } from "../types/app";

const TYPE_META: Record<string, { label: string; Icon: React.ElementType }> = {
  sow:        { label: "Statement of Work", Icon: FileText },
  pptx:       { label: "PowerPoint Deck",   Icon: Presentation },
  bid:        { label: "Bid Response",      Icon: FileText },
  case_study: { label: "Case Study",        Icon: BookMarked },
  register:   { label: "Data Register",     Icon: Layers },
};

const ShareView = () => {
  const { token } = useParams<{ token: string }>();
  const [link, setLink] = useState<ShareLinkRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) { setError("Invalid share link."); setLoading(false); return; }
    getSharedArtifact(token)
      .then(setLink)
      .catch((err) => setError(err instanceof Error ? err.message : "Share link not found or has expired."))
      .finally(() => setLoading(false));
  }, [token]);

  const handleDownload = () => {
    if (!link) return;
    const url = downloadArtifactUrl(link.download_url);
    const a = document.createElement("a");
    a.href = url;
    a.download = link.artifact_name;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const fmtDate = (iso: string) =>
    new Date(iso).toLocaleDateString(undefined, { dateStyle: "long" });

  if (loading) {
    return (
      <div style={pageStyle}>
        <div style={cardStyle}>
          <p style={{ color: "#888", textAlign: "center" }}>Loading…</p>
        </div>
      </div>
    );
  }

  if (error || !link) {
    return (
      <div style={pageStyle}>
        <div style={{ ...cardStyle, padding: "40px 32px" }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
            <AlertCircle size={36} style={{ color: "#dc2626" }} />
            <h2 style={{ margin: 0, fontSize: "1.1rem", color: "#333" }}>Link unavailable</h2>
            <p style={{ margin: 0, color: "#888", textAlign: "center", fontSize: "0.9rem" }}>
              {error ?? "This share link does not exist or has expired."}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const meta = TYPE_META[link.artifact_type] ?? TYPE_META.sow;
  const { Icon } = meta;

  return (
    <div style={pageStyle}>
      {/* Header bar */}
      <div style={{
        width: "100%", padding: "14px 24px", display: "flex", alignItems: "center", gap: "12px",
        background: "#fff", borderBottom: "1px solid #e5e7eb", boxSizing: "border-box",
      }}>
        <img src="/bsbi-logo.jpeg" alt="BSBI" style={{ height: "28px", objectFit: "contain" }} />
        <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "#1c1c1e" }}>BSBI Intelligence</span>
        <span style={{ color: "#ccc" }}>|</span>
        <span style={{ fontSize: "0.85rem", color: "#888" }}>Shared Document</span>
      </div>

      <div style={{ flex: 1, display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "40px 16px" }}>
        <div style={{ ...cardStyle, width: "100%", maxWidth: "560px" }}>
          {/* Type badge */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "20px" }}>
            <div style={{
              width: "40px", height: "40px", borderRadius: "10px",
              background: "rgba(177,18,35,0.08)", display: "flex", alignItems: "center", justifyContent: "center",
              color: "#b11223", flexShrink: 0,
            }}>
              <Icon size={20} />
            </div>
            <div>
              <div style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "#b11223" }}>
                {meta.label}
              </div>
              <div style={{ fontSize: "0.78rem", color: "#888", marginTop: "2px" }}>
                Shared {fmtDate(link.created_at)}
                {link.expires_at && ` · Expires ${fmtDate(link.expires_at)}`}
              </div>
            </div>
          </div>

          {/* Title */}
          <h1 style={{ margin: "0 0 10px", fontSize: "1.3rem", fontWeight: 700, color: "#1c1c1e", lineHeight: 1.3 }}>
            {link.artifact_name}
          </h1>

          {/* Summary */}
          {link.summary && (
            <p style={{ margin: "0 0 24px", fontSize: "0.88rem", color: "#555", lineHeight: 1.6 }}>
              {link.summary}
            </p>
          )}

          <hr style={{ border: "none", borderTop: "1px solid #e5e7eb", margin: "0 0 20px" }} />

          {/* Download */}
          <button
            type="button"
            onClick={handleDownload}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
              width: "100%", padding: "12px", borderRadius: "8px",
              background: "#b11223", color: "#fff", border: "none", cursor: "pointer",
              fontWeight: 600, fontSize: "0.92rem",
            }}
          >
            <Download size={16} />
            Download {link.artifact_name}
          </button>

          {/* Footer */}
          <div style={{ marginTop: "20px", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px", fontSize: "0.75rem", color: "#aaa" }}>
            <ExternalLink size={11} />
            Shared via BSBI Document Intelligence Platform
          </div>
        </div>
      </div>
    </div>
  );
};

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  display: "flex",
  flexDirection: "column",
  alignItems: "stretch",
  background: "#f4f4f6",
  fontFamily: "'Calibri', 'Segoe UI', sans-serif",
};

const cardStyle: React.CSSProperties = {
  background: "#fff",
  borderRadius: "12px",
  border: "1px solid #e5e7eb",
  padding: "28px",
  boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
};

export default ShareView;