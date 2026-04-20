import {
  Activity,
  AlertCircle,
  BarChart2,
  CheckCircle2,
  FileText,
  Library,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { useAppState } from "../context/AppStateContext";
import { getAnalytics } from "../services/api";
import type { AnalyticsDashboard, ActivityItem } from "../types/app";

const StatCard = ({ label, value, sub, icon }: { label: string; value: string | number; sub?: string; icon: React.ReactNode }) => (
  <div className="card" style={{ flex: 1, minWidth: 140 }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
      <div>
        <div style={{ fontSize: 28, fontWeight: 700, color: "var(--bsbi-red)" }}>{value}</div>
        <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 2 }}>{label}</div>
        {sub && <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>{sub}</div>}
      </div>
      <div style={{ color: "var(--text-muted)", opacity: 0.5 }}>{icon}</div>
    </div>
  </div>
);

const ActivityIcon = ({ type }: { type: ActivityItem["activity_type"] }) => {
  if (type === "document") return <FileText size={13} color="var(--bsbi-red)" />;
  if (type === "artifact") return <Library size={13} color="var(--status-pass)" />;
  if (type === "validation") return <CheckCircle2 size={13} color="var(--status-warn)" />;
  return <Activity size={13} color="var(--text-muted)" />;
};

const MiniBarChart = ({ data }: { data: { date: string; avg_score: number; count: number }[] }) => {
  if (!data.length) return <div style={{ color: "var(--text-muted)", fontSize: 13 }}>No data for the last 30 days.</div>;
  const maxScore = 10;
  const barWidth = Math.max(12, Math.min(40, Math.floor(600 / data.length) - 4));

  return (
    <div style={{ overflowX: "auto" }}>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 100, paddingBottom: 20, minWidth: data.length * (barWidth + 3) }}>
        {data.map((d, i) => {
          const height = Math.max(4, (d.avg_score / maxScore) * 80);
          const color = d.avg_score >= 8 ? "var(--status-pass)" : d.avg_score >= 6 ? "var(--status-warn)" : "var(--status-fail)";
          return (
            <div key={i} style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div title={`${d.date}: avg ${d.avg_score.toFixed(1)}, ${d.count} validations`} style={{ width: barWidth, height, background: color, borderRadius: "3px 3px 0 0", cursor: "default" }} />
              <div style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 3, whiteSpace: "nowrap", transform: "rotate(-45deg)", transformOrigin: "top left", position: "absolute", top: "100%", left: 4 }}>
                {d.date.slice(5)}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", gap: 12, marginTop: 8, fontSize: 11 }}>
        <span style={{ color: "var(--status-pass)" }}>■ ≥ 8 Pass</span>
        <span style={{ color: "var(--status-warn)" }}>■ 6–7 Warn</span>
        <span style={{ color: "var(--status-fail)" }}>■ &lt; 6 Fail</span>
      </div>
    </div>
  );
};

const AnalyticsView = () => {
  const { token } = useAppState();
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAnalytics({ token });
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load analytics.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
        <div>
          <h1 className="page-title">
            <BarChart2 size={20} color="var(--bsbi-red)" style={{ marginRight: 8 }} />
            Analytics & Insights
          </h1>
          <p className="page-subtitle">
            Organisation-level view of document activity, validation quality, and common issues.
          </p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => void load()} disabled={loading}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {loading && (
        <div className="validate-empty">
          <Loader2 size={36} className="spin" />
          <h2>Loading analytics…</h2>
        </div>
      )}

      {error && (
        <div className="message error" style={{ marginBottom: 16 }}>
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {data && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

          {/* ── Overview stats ── */}
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <StatCard label="Documents Parsed" value={data.overview.total_documents} icon={<FileText size={24} />} />
            <StatCard label="Artifacts Generated" value={data.overview.total_artifacts} icon={<Library size={24} />} />
            <StatCard label="Validations Run" value={data.overview.total_validations} icon={<CheckCircle2 size={24} />} />
            <StatCard
              label="Avg Quality Score"
              value={data.overview.avg_compliance_score.toFixed(1)}
              sub="out of 10"
              icon={<BarChart2 size={24} />}
            />
            <StatCard
              label="Pass Rate"
              value={`${data.overview.pass_rate}%`}
              sub="pass or pass with warnings"
              icon={<Activity size={24} />}
            />
            <StatCard label="Saved Clauses" value={data.overview.total_clauses} icon={<FileText size={24} />} />
          </div>

          {/* ── Validation trends ── */}
          <div className="card">
            <h3 className="card-title">Validation Quality — Last 30 Days</h3>
            <MiniBarChart data={data.validation_trends} />
          </div>

          {/* ── Common issues + Activity ── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div className="card">
              <h3 className="card-title">Most Common Issues</h3>
              {data.common_issues.length === 0 ? (
                <p style={{ color: "var(--text-muted)", fontSize: 13 }}>No validation issues recorded yet.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {data.common_issues.map((issue, i) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                      <span style={{ fontSize: 12, flex: 1, lineHeight: 1.4 }}>{issue.issue}</span>
                      <span style={{ background: "var(--surface-secondary)", borderRadius: 4, padding: "2px 7px", fontSize: 11, fontWeight: 600, whiteSpace: "nowrap" }}>×{issue.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="card">
              <h3 className="card-title">Recent Activity</h3>
              {data.recent_activity.length === 0 ? (
                <p style={{ color: "var(--text-muted)", fontSize: 13 }}>No activity yet.</p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 320, overflowY: "auto" }}>
                  {data.recent_activity.map((item, i) => (
                    <div key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                      <div style={{ marginTop: 2 }}><ActivityIcon type={item.activity_type} /></div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 12, fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.name}</div>
                        <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{item.details}</div>
                      </div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)", whiteSpace: "nowrap" }}>{item.created_at.slice(0, 10)}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalyticsView;