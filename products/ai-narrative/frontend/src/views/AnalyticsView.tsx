import {
  AlertCircle,
  BarChart3,
  CheckCircle2,
  Download,
  Loader2,
  TrendingDown,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useAppState } from "../context/AppStateContext";
import { exportDriftCsv, getAnalytics, getDriftMetrics } from "../services/api";
import type { AnalyticsDashboard, DriftMetrics } from "../types/app";

const verdictColour = (v: string) =>
  v === "PASS" ? "var(--status-pass)" : v === "PASS_WITH_WARNINGS" ? "var(--status-warn)" : "var(--status-fail)";

const VerdictIcon = ({ verdict }: { verdict: string }) => {
  if (verdict === "PASS") return <CheckCircle2 size={14} color="var(--status-pass)" />;
  if (verdict === "PASS_WITH_WARNINGS") return <AlertCircle size={14} color="var(--status-warn)" />;
  return <XCircle size={14} color="var(--status-fail)" />;
};

/* ── SVG line chart ────────────────────────────────────────────────────────── */

function ScoreTrendChart({ metrics }: { metrics: DriftMetrics }) {
  const pts = metrics.data_points.filter((d) => d.avg_score !== null && d.total > 0);
  if (pts.length < 2) {
    return (
      <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-muted)", fontSize: "0.84rem" }}>
        Not enough data to draw a trend line (need ≥ 2 scored days).
      </div>
    );
  }

  const W = 620, H = 180, PX = 40, PY = 20;
  const scores = pts.map((d) => d.avg_score as number);
  const minS = Math.max(0, Math.min(...scores) - 0.5);
  const maxS = Math.min(10, Math.max(...scores) + 0.5);
  const toX = (i: number) => PX + (i / (pts.length - 1)) * (W - PX * 2);
  const toY = (s: number) => PY + (1 - (s - minS) / (maxS - minS)) * (H - PY * 2);

  const polyline = pts.map((d, i) => `${toX(i)},${toY(d.avg_score as number)}`).join(" ");

  const changeSet = new Set(metrics.provider_changes.map((c) => c.date));

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: H, display: "block" }}>
      {/* Y-axis guides */}
      {[minS, (minS + maxS) / 2, maxS].map((v) => (
        <g key={v}>
          <line x1={PX} y1={toY(v)} x2={W - PX} y2={toY(v)} stroke="var(--border)" strokeWidth={1} strokeDasharray="4 4" />
          <text x={PX - 6} y={toY(v) + 4} textAnchor="end" fontSize={10} fill="var(--text-muted)">{v.toFixed(1)}</text>
        </g>
      ))}

      {/* Provider change markers */}
      {pts.map((d, i) =>
        changeSet.has(d.date) ? (
          <line key={d.date} x1={toX(i)} y1={PY} x2={toX(i)} y2={H - PY} stroke="var(--status-warn)" strokeWidth={1.5} strokeDasharray="3 3" opacity={0.7} />
        ) : null
      )}

      {/* Score line */}
      <polyline points={polyline} fill="none" stroke="var(--bsbi-red)" strokeWidth={2} strokeLinejoin="round" />

      {/* Data points */}
      {pts.map((d, i) => (
        <circle key={i} cx={toX(i)} cy={toY(d.avg_score as number)} r={3.5} fill="var(--bsbi-red)" stroke="var(--card-bg)" strokeWidth={1.5}>
          <title>{d.date}: {(d.avg_score as number).toFixed(2)}</title>
        </circle>
      ))}

      {/* X-axis labels — show first, mid, last */}
      {[0, Math.floor((pts.length - 1) / 2), pts.length - 1].map((i) => (
        <text key={i} x={toX(i)} y={H - 4} textAnchor="middle" fontSize={10} fill="var(--text-muted)">
          {pts[i].date.slice(5)}
        </text>
      ))}
    </svg>
  );
}

/* ── Main component ─────────────────────────────────────────────────────────── */

type Tab = "overview" | "drift";

export default function AnalyticsView() {
  const { token } = useAppState();
  const [tab, setTab] = useState<Tab>("overview");

  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [dataLoading, setDataLoading] = useState(true);
  const [dataError, setDataError] = useState<string | null>(null);

  const [drift, setDrift] = useState<DriftMetrics | null>(null);
  const [driftLoading, setDriftLoading] = useState(false);
  const [driftError, setDriftError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    getAnalytics({ token })
      .then(setData)
      .catch((err) => setDataError(err instanceof Error ? err.message : "Failed to load analytics."))
      .finally(() => setDataLoading(false));
  }, [token]);

  useEffect(() => {
    if (tab !== "drift" || drift) return;
    setDriftLoading(true);
    getDriftMetrics({ token })
      .then(setDrift)
      .catch((err) => setDriftError(err instanceof Error ? err.message : "Failed to load drift data."))
      .finally(() => setDriftLoading(false));
  }, [tab, token, drift]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await exportDriftCsv({ token });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `drift_audit_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  const tabStyle = (t: Tab): React.CSSProperties => ({
    padding: "7px 18px",
    border: "none",
    cursor: "pointer",
    fontWeight: tab === t ? 700 : 400,
    fontSize: "0.88rem",
    borderBottom: tab === t ? "2px solid var(--bsbi-red)" : "2px solid transparent",
    background: "none",
    color: tab === t ? "var(--bsbi-red)" : "var(--text-muted)",
    transition: "color 0.15s",
  });

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title"><BarChart3 size={20} color="var(--bsbi-red)" /> Analytics</h1>
        <p className="page-subtitle">Overview of your narrative scoring activity.</p>
      </div>

      {/* Tab bar */}
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--border)", marginBottom: 20 }}>
        <button type="button" style={tabStyle("overview")} onClick={() => setTab("overview")}>Overview</button>
        <button type="button" style={tabStyle("drift")} onClick={() => setTab("drift")}>AI Performance Drift</button>
      </div>

      {/* ── Overview tab ──────────────────────────────────────────────────────── */}
      {tab === "overview" && (
        <>
          {dataLoading ? (
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}><Loader2 size={20} className="spin" /> Loading analytics…</div>
          ) : dataError ? (
            <div className="message error"><AlertCircle size={14} /> {dataError}</div>
          ) : (
            <>
              <div className="analytics-grid">
                <div className="metric-card">
                  <div className="metric-label">Total Scored</div>
                  <div className="metric-value">{data!.overview.total_scored}</div>
                  <div className="metric-sub">narratives</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Pass</div>
                  <div className="metric-value" style={{ color: "var(--status-pass)" }}>{data!.overview.pass_count}</div>
                  <div className="metric-sub">score ≥ 8</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Warnings</div>
                  <div className="metric-value" style={{ color: "var(--status-warn)" }}>{data!.overview.warn_count}</div>
                  <div className="metric-sub">score 6–7</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Fail</div>
                  <div className="metric-value" style={{ color: "var(--status-fail)" }}>{data!.overview.fail_count}</div>
                  <div className="metric-sub">score &lt; 6</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Avg Score</div>
                  <div className="metric-value">{data!.overview.avg_compliance_score.toFixed(1)}</div>
                  <div className="metric-sub">/ 10</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Reference Files</div>
                  <div className="metric-value">{data!.overview.reference_files_count}</div>
                  <div className="metric-sub">indexed</div>
                </div>
              </div>

              {data!.overview.total_scored > 0 && (
                <div className="card" style={{ marginBottom: 20 }}>
                  <h3 className="card-title">Pass Rate</h3>
                  <div style={{ display: "flex", height: 20, borderRadius: 10, overflow: "hidden", gap: 2 }}>
                    {data!.overview.pass_count > 0 && (
                      <div style={{ flex: data!.overview.pass_count, background: "var(--status-pass)" }} title={`Pass: ${data!.overview.pass_count}`} />
                    )}
                    {data!.overview.warn_count > 0 && (
                      <div style={{ flex: data!.overview.warn_count, background: "var(--status-warn)" }} title={`Warnings: ${data!.overview.warn_count}`} />
                    )}
                    {data!.overview.fail_count > 0 && (
                      <div style={{ flex: data!.overview.fail_count, background: "var(--status-fail)" }} title={`Fail: ${data!.overview.fail_count}`} />
                    )}
                  </div>
                  <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: "0.78rem", color: "var(--text-muted)" }}>
                    <span style={{ color: "var(--status-pass)" }}>● Pass {Math.round((data!.overview.pass_count / data!.overview.total_scored) * 100)}%</span>
                    <span style={{ color: "var(--status-warn)" }}>● Warn {Math.round((data!.overview.warn_count / data!.overview.total_scored) * 100)}%</span>
                    <span style={{ color: "var(--status-fail)" }}>● Fail {Math.round((data!.overview.fail_count / data!.overview.total_scored) * 100)}%</span>
                  </div>
                </div>
              )}

              <div className="card">
                <h3 className="card-title">Recent Scores</h3>
                {data!.recent_scores.length === 0 ? (
                  <p style={{ color: "var(--text-muted)", fontSize: "0.88rem" }}>No scores yet.</p>
                ) : (
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.84rem" }}>
                    <thead>
                      <tr>
                        {["ID", "Document", "Verdict", "Score", "Date"].map((h) => (
                          <th key={h} style={{ textAlign: "left", padding: "8px 10px", borderBottom: "1px solid var(--border-color)", color: "var(--text-muted)", fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase" }}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {data!.recent_scores.map((s) => (
                        <tr key={s.id} style={{ borderBottom: "1px solid var(--border-color)" }}>
                          <td style={{ padding: "8px 10px", fontFamily: "monospace", fontSize: "0.8rem" }}>{s.unique_id}</td>
                          <td style={{ padding: "8px 10px" }}>{s.document_name}</td>
                          <td style={{ padding: "8px 10px" }}>
                            <span style={{ display: "flex", alignItems: "center", gap: 5, color: verdictColour(s.overall_verdict), fontWeight: 600, fontSize: "0.82rem" }}>
                              <VerdictIcon verdict={s.overall_verdict} />
                              {s.overall_verdict === "PASS_WITH_WARNINGS" ? "WARN" : s.overall_verdict}
                            </span>
                          </td>
                          <td style={{ padding: "8px 10px", fontWeight: 600 }}>{s.compliance_score.toFixed(1)}</td>
                          <td style={{ padding: "8px 10px", color: "var(--text-muted)" }}>
                            {new Date(s.created_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </>
          )}
        </>
      )}

      {/* ── Drift tab ─────────────────────────────────────────────────────────── */}
      {tab === "drift" && (
        <>
          {driftLoading ? (
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}><Loader2 size={20} className="spin" /> Loading drift data…</div>
          ) : driftError ? (
            <div className="message error"><AlertCircle size={14} /> {driftError}</div>
          ) : drift ? (
            <>
              {/* Key stats */}
              <div className="analytics-grid" style={{ marginBottom: 20 }}>
                <div className="metric-card">
                  <div className="metric-label">Avg Score (30d)</div>
                  <div className="metric-value">{drift.avg_score.toFixed(2)}</div>
                  <div className="metric-sub">/ 10</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Score Variance</div>
                  <div className="metric-value">{drift.score_variance.toFixed(3)}</div>
                  <div className="metric-sub">std dev proxy</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Trend</div>
                  <div className="metric-value" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "1.1rem",
                    color: drift.trend_direction === "improving" ? "var(--status-pass)" : drift.trend_direction === "declining" ? "var(--status-fail)" : "var(--text-muted)" }}>
                    {drift.trend_direction === "improving" ? <TrendingUp size={18} /> : drift.trend_direction === "declining" ? <TrendingDown size={18} /> : "→"}
                    {drift.trend_direction.charAt(0).toUpperCase() + drift.trend_direction.slice(1)}
                  </div>
                  <div className="metric-sub">30-day linear</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Custom Rules Usage</div>
                  <div className="metric-value">{drift.custom_rules_usage_pct.toFixed(0)}%</div>
                  <div className="metric-sub">of scored narratives</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Financial Check Usage</div>
                  <div className="metric-value">{drift.financial_check_usage_pct.toFixed(0)}%</div>
                  <div className="metric-sub">Layer 3 active</div>
                </div>
                <div className="metric-card">
                  <div className="metric-label">Total Scored (30d)</div>
                  <div className="metric-value">{drift.total_scored}</div>
                  <div className="metric-sub">narratives</div>
                </div>
              </div>

              {/* Score trend chart */}
              <div className="card" style={{ marginBottom: 20 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <h3 className="card-title" style={{ margin: 0 }}>Daily Average Compliance Score</h3>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: "0.78rem", display: "flex", alignItems: "center", gap: 5 }}
                    onClick={() => void handleExport()}
                    disabled={exporting}
                  >
                    {exporting ? <Loader2 size={13} className="spin" /> : <Download size={13} />}
                    Export CSV
                  </button>
                </div>
                {drift.provider_changes.length > 0 && (
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 8 }}>
                    <span style={{ borderBottom: "1px dashed var(--status-warn)", paddingBottom: 1 }}>Dashed vertical lines</span> mark provider changes.
                  </div>
                )}
                <ScoreTrendChart metrics={drift} />
              </div>

              {/* Daily verdict distribution */}
              {drift.data_points.some((d) => d.total > 0) && (
                <div className="card" style={{ marginBottom: 20 }}>
                  <h3 className="card-title">Daily Verdict Distribution</h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {drift.data_points.filter((d) => d.total > 0).map((d) => (
                      <div key={d.date} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.78rem" }}>
                        <span style={{ width: 50, color: "var(--text-muted)", flexShrink: 0 }}>{d.date.slice(5)}</span>
                        <div style={{ flex: 1, display: "flex", height: 14, borderRadius: 4, overflow: "hidden", gap: 1 }}>
                          {d.pass_count > 0 && (
                            <div style={{ flex: d.pass_count, background: "var(--status-pass)" }} title={`Pass: ${d.pass_count}`} />
                          )}
                          {d.warn_count > 0 && (
                            <div style={{ flex: d.warn_count, background: "var(--status-warn)" }} title={`Warn: ${d.warn_count}`} />
                          )}
                          {d.fail_count > 0 && (
                            <div style={{ flex: d.fail_count, background: "var(--status-fail)" }} title={`Fail: ${d.fail_count}`} />
                          )}
                        </div>
                        <span style={{ width: 24, textAlign: "right", color: "var(--text-muted)" }}>{d.total}</span>
                        {d.avg_score !== null && (
                          <span style={{ width: 32, textAlign: "right", fontWeight: 600 }}>{d.avg_score.toFixed(1)}</span>
                        )}
                      </div>
                    ))}
                  </div>
                  <div style={{ display: "flex", gap: 14, marginTop: 10, fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    <span style={{ color: "var(--status-pass)" }}>● Pass</span>
                    <span style={{ color: "var(--status-warn)" }}>● Warn</span>
                    <span style={{ color: "var(--status-fail)" }}>● Fail</span>
                  </div>
                </div>
              )}

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
                {/* Model distribution */}
                <div className="card">
                  <h3 className="card-title">Model Distribution (30d)</h3>
                  {Object.keys(drift.model_distribution).length === 0 ? (
                    <p style={{ color: "var(--text-muted)", fontSize: "0.84rem" }}>No data.</p>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {Object.entries(drift.model_distribution)
                        .sort((a, b) => b[1] - a[1])
                        .map(([model, count]) => {
                          const total = Object.values(drift.model_distribution).reduce((a, b) => a + b, 0);
                          const pct = Math.round((count / total) * 100);
                          return (
                            <div key={model}>
                              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: 3 }}>
                                <span style={{ fontFamily: "monospace" }}>{model}</span>
                                <span style={{ color: "var(--text-muted)" }}>{count} ({pct}%)</span>
                              </div>
                              <div style={{ height: 6, borderRadius: 3, background: "var(--bg-subtle)", overflow: "hidden" }}>
                                <div style={{ height: "100%", width: `${pct}%`, background: "var(--bsbi-red)", borderRadius: 3 }} />
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  )}
                </div>

                {/* Provider changes */}
                <div className="card">
                  <h3 className="card-title">Provider Changes (30d)</h3>
                  {drift.provider_changes.length === 0 ? (
                    <p style={{ color: "var(--text-muted)", fontSize: "0.84rem" }}>No provider changes detected.</p>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {drift.provider_changes.map((c, i) => (
                        <div key={i} style={{ fontSize: "0.82rem", padding: "6px 10px", borderRadius: 6, background: "var(--bg-subtle)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span>
                            <span style={{ fontFamily: "monospace", color: "var(--status-fail)" }}>{c.from_provider}</span>
                            {" → "}
                            <span style={{ fontFamily: "monospace", color: "var(--status-pass)" }}>{c.to_provider}</span>
                          </span>
                          <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>{c.date}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : null}
        </>
      )}
    </div>
  );
}