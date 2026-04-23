import { AlertCircle, BarChart3, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useAppState } from "../context/AppStateContext";
import { getAnalytics } from "../services/api";
import type { AnalyticsDashboard } from "../types/app";

const verdictColour = (v: string) =>
  v === "PASS" ? "var(--status-pass)" : v === "PASS_WITH_WARNINGS" ? "var(--status-warn)" : "var(--status-fail)";

const VerdictIcon = ({ verdict }: { verdict: string }) => {
  if (verdict === "PASS") return <CheckCircle2 size={14} color="var(--status-pass)" />;
  if (verdict === "PASS_WITH_WARNINGS") return <AlertCircle size={14} color="var(--status-warn)" />;
  return <XCircle size={14} color="var(--status-fail)" />;
};

export default function AnalyticsView() {
  const { token } = useAppState();
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAnalytics({ token })
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load analytics."))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) return (
    <div className="page-container" style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <Loader2 size={20} className="spin" /> Loading analytics…
    </div>
  );

  if (error) return (
    <div className="page-container">
      <div className="message error"><AlertCircle size={14} /> {error}</div>
    </div>
  );

  const { overview, recent_scores } = data!;

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title"><BarChart3 size={20} color="var(--bsbi-red)" /> Analytics</h1>
        <p className="page-subtitle">Overview of your narrative scoring activity.</p>
      </div>

      {/* Overview metrics */}
      <div className="analytics-grid">
        <div className="metric-card">
          <div className="metric-label">Total Scored</div>
          <div className="metric-value">{overview.total_scored}</div>
          <div className="metric-sub">narratives</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Pass</div>
          <div className="metric-value" style={{ color: "var(--status-pass)" }}>{overview.pass_count}</div>
          <div className="metric-sub">score ≥ 8</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Warnings</div>
          <div className="metric-value" style={{ color: "var(--status-warn)" }}>{overview.warn_count}</div>
          <div className="metric-sub">score 6–7</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Fail</div>
          <div className="metric-value" style={{ color: "var(--status-fail)" }}>{overview.fail_count}</div>
          <div className="metric-sub">score &lt; 6</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Avg Score</div>
          <div className="metric-value">{overview.avg_compliance_score.toFixed(1)}</div>
          <div className="metric-sub">/ 10</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Reference Files</div>
          <div className="metric-value">{overview.reference_files_count}</div>
          <div className="metric-sub">indexed</div>
        </div>
      </div>

      {/* Pass rate bar */}
      {overview.total_scored > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 className="card-title">Pass Rate</h3>
          <div style={{ display: "flex", height: 20, borderRadius: 10, overflow: "hidden", gap: 2 }}>
            {overview.pass_count > 0 && (
              <div style={{ flex: overview.pass_count, background: "var(--status-pass)" }} title={`Pass: ${overview.pass_count}`} />
            )}
            {overview.warn_count > 0 && (
              <div style={{ flex: overview.warn_count, background: "var(--status-warn)" }} title={`Warnings: ${overview.warn_count}`} />
            )}
            {overview.fail_count > 0 && (
              <div style={{ flex: overview.fail_count, background: "var(--status-fail)" }} title={`Fail: ${overview.fail_count}`} />
            )}
          </div>
          <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: "0.78rem", color: "var(--text-muted)" }}>
            <span style={{ color: "var(--status-pass)" }}>● Pass {Math.round((overview.pass_count / overview.total_scored) * 100)}%</span>
            <span style={{ color: "var(--status-warn)" }}>● Warn {Math.round((overview.warn_count / overview.total_scored) * 100)}%</span>
            <span style={{ color: "var(--status-fail)" }}>● Fail {Math.round((overview.fail_count / overview.total_scored) * 100)}%</span>
          </div>
        </div>
      )}

      {/* Recent activity */}
      <div className="card">
        <h3 className="card-title">Recent Scores</h3>
        {recent_scores.length === 0 ? (
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
              {recent_scores.map((s) => (
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
    </div>
  );
}