import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  Download,
  FileText,
  FolderOpen,
  Layers,
  Loader2,
  Presentation,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useAppState } from "../context/AppStateContext";
import { downloadArtifact, getProjectOverview, getValidationDetail } from "../services/api";
import type { ProjectOverview, ValidationDetail } from "../types/app";

type Tab = "documents" | "artifacts" | "validations" | "clauses";

const ARTIFACT_ICONS: Record<string, React.ElementType> = {
  sow: FileText,
  pptx: Presentation,
  bid: FileText,
  case_study: BookOpen,
  register: Layers,
};

const VERDICT_STYLE: Record<string, { color: string; Icon: React.ElementType }> = {
  PASS:               { color: "#16a34a", Icon: CheckCircle },
  PASS_WITH_WARNINGS: { color: "#d97706", Icon: CheckCircle },
  FAIL:               { color: "#dc2626", Icon: XCircle },
};

const fmtDate = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

const ProjectDetailView = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const { token } = useAppState();
  const navigate = useNavigate();

  const [overview, setOverview] = useState<ProjectOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("documents");
  const [downloading, setDownloading] = useState<string | null>(null);
  const [expandedValId, setExpandedValId] = useState<number | null>(null);
  const [valDetails, setValDetails] = useState<Record<number, ValidationDetail>>({});
  const [valLoading, setValLoading] = useState<number | null>(null);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    getProjectOverview(Number(projectId), { token })
      .then(setOverview)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load project."))
      .finally(() => setLoading(false));
  }, [projectId, token]);

  const handleDownload = async (downloadUrl: string, artifactName: string) => {
    setDownloading(artifactName);
    try {
      await downloadArtifact(downloadUrl, artifactName, { token });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed.");
    } finally {
      setDownloading(null);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="card" style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Loading project…
        </div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="page-container">
        <div className="message error">
          <AlertCircle size={15} />
          <span>{error ?? "Project not found."}</span>
        </div>
      </div>
    );
  }

  const tabs: { key: Tab; label: string; count: number; Icon: React.ElementType }[] = [
    { key: "documents",   label: "Documents",   count: overview.documents.length,            Icon: FileText },
    { key: "artifacts",   label: "Artifacts",   count: overview.artifacts.length,            Icon: Layers },
    { key: "validations", label: "Validations", count: overview.recent_validations.length,   Icon: ClipboardCheck },
    { key: "clauses",     label: "Clauses",     count: overview.clause_count,                Icon: BookOpen },
  ];

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header" style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
        <button
          className="btn btn-secondary"
          type="button"
          onClick={() => navigate("/projects")}
          style={{ flexShrink: 0, marginTop: "2px" }}
        >
          <ArrowLeft size={14} />
        </button>
        <div>
          <h1 className="page-title" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <FolderOpen size={22} style={{ color: "var(--bsbi-red)" }} />
            {overview.name}
          </h1>
          <p className="page-subtitle">
            Created {fmtDate(overview.created_at)} &nbsp;·&nbsp; Last updated {fmtDate(overview.updated_at)}
          </p>
        </div>
      </div>

      {/* Tab bar */}
      <div style={{ display: "flex", gap: "4px", marginBottom: "20px", borderBottom: "2px solid var(--border-color)", paddingBottom: "0" }}>
        {tabs.map(({ key, label, count, Icon }) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            style={{
              display: "flex", alignItems: "center", gap: "6px",
              padding: "8px 16px", background: "none", border: "none",
              borderBottom: activeTab === key ? "2px solid var(--bsbi-red)" : "2px solid transparent",
              color: activeTab === key ? "var(--bsbi-red)" : "var(--text-muted)",
              fontWeight: activeTab === key ? 600 : 400,
              fontSize: "0.87rem", cursor: "pointer", marginBottom: "-2px",
              transition: "color 0.15s",
            }}
          >
            <Icon size={14} />
            {label}
            <span style={{
              background: activeTab === key ? "var(--bsbi-red)" : "var(--border-color)",
              color: activeTab === key ? "#fff" : "var(--text-muted)",
              borderRadius: "10px", padding: "1px 7px", fontSize: "0.73rem", fontWeight: 600,
            }}>
              {count}
            </span>
          </button>
        ))}
      </div>

      {/* Documents tab */}
      {activeTab === "documents" && (
        overview.documents.length === 0 ? (
          <div className="card library-empty">
            <FileText size={32} strokeWidth={1.3} />
            <h2>No documents yet</h2>
            <p>Upload documents in Studio and assign them to this project.</p>
          </div>
        ) : (
          <div className="library-grid">
            {overview.documents.map((doc) => (
              <article key={doc.id} className="card library-card">
                <div className="library-card-top">
                  <div className="library-card-icon badge-sow">
                    <FileText size={18} />
                  </div>
                </div>
                <h3 className="library-card-title">{doc.title || doc.filename}</h3>
                <div className="library-card-meta">
                  <span>{doc.filename}</span>
                  <span>{doc.word_count.toLocaleString()} words</span>
                </div>
                <div className="library-card-meta" style={{ marginTop: "4px" }}>
                  <span>{fmtDate(doc.created_at)}</span>
                </div>
              </article>
            ))}
          </div>
        )
      )}

      {/* Artifacts tab */}
      {activeTab === "artifacts" && (
        overview.artifacts.length === 0 ? (
          <div className="card library-empty">
            <Layers size={32} strokeWidth={1.3} />
            <h2>No artifacts yet</h2>
            <p>Generated deliverables (SOW, PPT, Bid, Case Study) linked to this project will appear here.</p>
          </div>
        ) : (
          <div className="library-grid">
            {overview.artifacts.map((art) => {
              const Icon = ARTIFACT_ICONS[art.artifact_type] ?? FileText;
              return (
                <article key={art.id} className="card library-card">
                  <div className="library-card-top">
                    <div className="library-card-icon badge-sow">
                      <Icon size={18} />
                    </div>
                    <span className="artifact-type-badge badge-sow" style={{ textTransform: "uppercase", fontSize: "0.7rem" }}>
                      {art.artifact_type}
                    </span>
                  </div>
                  <h3 className="library-card-title">{art.summary || art.artifact_name}</h3>
                  <div className="library-card-meta">
                    <span>{art.artifact_name}</span>
                    <span>{fmtDate(art.created_at)}</span>
                  </div>
                  <button
                    className="btn btn-primary library-download-btn"
                    type="button"
                    onClick={() => handleDownload(art.download_url, art.artifact_name)}
                    disabled={downloading === art.artifact_name}
                    style={{ marginTop: "auto" }}
                  >
                    <Download size={13} />
                    {downloading === art.artifact_name ? "Downloading…" : "Download"}
                  </button>
                </article>
              );
            })}
          </div>
        )
      )}

      {/* Validations tab */}
      {activeTab === "validations" && (
        overview.recent_validations.length === 0 ? (
          <div className="card library-empty">
            <ClipboardCheck size={32} strokeWidth={1.3} />
            <h2>No validations yet</h2>
            <p>Run a document through Validate to see results here.</p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {overview.recent_validations.map((v) => {
              const vs = VERDICT_STYLE[v.overall_verdict] ?? VERDICT_STYLE.FAIL;
              const { Icon } = vs;
              const isExpanded = expandedValId === v.id;
              const detail = valDetails[v.id];
              const isLoadingThis = valLoading === v.id;

              const handleToggle = async () => {
                if (isExpanded) {
                  setExpandedValId(null);
                  return;
                }
                setExpandedValId(v.id);
                if (!valDetails[v.id]) {
                  setValLoading(v.id);
                  try {
                    const d = await getValidationDetail(v.id, { token });
                    setValDetails((prev) => ({ ...prev, [v.id]: d }));
                  } catch {
                    // detail unavailable — row stays open but empty
                  } finally {
                    setValLoading(null);
                  }
                }
              };

              return (
                <div key={v.id} className="card" style={{ padding: 0, overflow: "hidden" }}>
                  {/* Summary row — clickable */}
                  <button
                    type="button"
                    onClick={() => void handleToggle()}
                    style={{
                      width: "100%", display: "flex", alignItems: "center", gap: "14px",
                      padding: "16px 20px", background: "none", border: "none",
                      cursor: "pointer", textAlign: "left",
                      borderBottom: isExpanded ? "1px solid var(--border-color)" : "none",
                    }}
                  >
                    <Icon size={20} style={{ color: vs.color, flexShrink: 0 }} />

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, fontSize: "0.9rem", marginBottom: "3px", color: "var(--text-primary)" }}>
                        {v.document_name}
                      </div>
                      <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", display: "flex", gap: "12px", alignItems: "center" }}>
                        {/* Score shown as X.X / 10 — matches ValidateView */}
                        <span>
                          Score:{" "}
                          <strong style={{ color: vs.color, fontFamily: "var(--font-mono, monospace)" }}>
                            {v.compliance_score.toFixed(1)}&thinsp;/&thinsp;10
                          </strong>
                        </span>
                        <span>{fmtDate(v.created_at)}</span>
                      </div>
                    </div>

                    <span style={{
                      fontSize: "0.75rem", fontWeight: 600, color: vs.color,
                      background: `${vs.color}18`, border: `1px solid ${vs.color}40`,
                      borderRadius: "12px", padding: "3px 10px", flexShrink: 0,
                    }}>
                      {v.overall_verdict.replace(/_/g, " ")}
                    </span>

                    {isLoadingThis
                      ? <Loader2 size={15} className="spin" style={{ color: "var(--text-muted)", flexShrink: 0 }} />
                      : isExpanded
                        ? <ChevronDown size={15} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
                        : <ChevronRight size={15} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
                    }
                  </button>

                  {/* Expanded detail panel */}
                  {isExpanded && detail && (
                    <div style={{ padding: "16px 20px", display: "flex", flexDirection: "column", gap: "16px" }}>

                      {/* Rubric + chunks */}
                      <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", display: "flex", gap: "16px" }}>
                        {detail.rubric_name && <span>Rubric: <strong style={{ color: "var(--text-secondary)" }}>{detail.rubric_name}</strong></span>}
                        {detail.meta?.chunks_used != null && <span>Context chunks used: <strong style={{ color: "var(--text-secondary)" }}>{detail.meta.chunks_used}</strong></span>}
                      </div>

                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                        {/* Issues */}
                        {detail.layer1.issues.length > 0 && (
                          <div>
                            <div style={{ fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--text-muted)", marginBottom: "8px" }}>
                              Layer 1 — Issues
                            </div>
                            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: "5px" }}>
                              {detail.layer1.issues.map((issue, i) => (
                                <li key={i} style={{ display: "flex", gap: "8px", fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                                  <span style={{ color: "#dc2626", flexShrink: 0, marginTop: "1px" }}>✗</span>
                                  {issue}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Passed */}
                        {detail.layer1.passed.length > 0 && (
                          <div>
                            <div style={{ fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--text-muted)", marginBottom: "8px" }}>
                              Layer 1 — Passed
                            </div>
                            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: "5px" }}>
                              {detail.layer1.passed.map((p, i) => (
                                <li key={i} style={{ display: "flex", gap: "8px", fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                                  <span style={{ color: "#16a34a", flexShrink: 0, marginTop: "1px" }}>✓</span>
                                  {p}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>

                      {/* Layer 2 consistency issues */}
                      {detail.layer2.consistency_issues.length > 0 && (
                        <div>
                          <div style={{ fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--text-muted)", marginBottom: "8px" }}>
                            Layer 2 — Consistency Issues
                          </div>
                          <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: "5px" }}>
                            {detail.layer2.consistency_issues.map((issue, i) => (
                              <li key={i} style={{ display: "flex", gap: "8px", fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                                <span style={{ color: "#d97706", flexShrink: 0, marginTop: "1px" }}>⚠</span>
                                {issue}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Rewritten text */}
                      {detail.rewritten_text && (
                        <div>
                          <div style={{ fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--text-muted)", marginBottom: "8px" }}>
                            AI-Suggested Rewrite
                          </div>
                          <div style={{
                            background: "var(--bg-secondary)", border: "1px solid var(--border-color)",
                            borderLeft: "3px solid var(--accent)", borderRadius: "6px",
                            padding: "12px 16px", fontSize: "0.83rem", color: "var(--text-secondary)",
                            lineHeight: 1.65, whiteSpace: "pre-wrap", maxHeight: "220px", overflowY: "auto",
                          }}>
                            {detail.rewritten_text}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )
      )}

      {/* Clauses tab */}
      {activeTab === "clauses" && (
        <div className="card library-empty">
          <BookOpen size={32} strokeWidth={1.3} />
          {overview.clause_count > 0 ? (
            <>
              <h2>{overview.clause_count} clause{overview.clause_count !== 1 ? "s" : ""} in this project</h2>
              <p>
                View and search them in the{" "}
                <button
                  type="button"
                  onClick={() => navigate("/clauses")}
                  style={{ background: "none", border: "none", color: "var(--bsbi-red)", cursor: "pointer", fontWeight: 600, padding: 0, fontSize: "inherit" }}
                >
                  Clause Library
                </button>
                .
              </p>
            </>
          ) : (
            <>
              <h2>No clauses yet</h2>
              <p>Auto-extract reusable clauses from project documents in the Clause Library.</p>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default ProjectDetailView;