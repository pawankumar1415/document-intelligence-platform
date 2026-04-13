import {
  AlertCircle,
  BookMarked,
  Download,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import { useState } from "react";

import { useAppState } from "../context/AppStateContext";
import { downloadArtifact, generateCaseStudy } from "../services/api";
import type { CaseStudyMetric, GenerateResult } from "../types/app";

const INDUSTRY_OPTIONS = [
  "Housing & Social Care",
  "Financial Services",
  "NHS & Healthcare",
  "Local Government",
  "Central Government",
  "Education",
  "Infrastructure & Utilities",
  "Retail & Consumer",
  "Technology",
  "Other",
];

const CaseStudyView = () => {
  const { token, llmProvider, llmModel, parsedDocument, projectId } = useAppState();

  // Core fields
  const [clientName, setClientName] = useState("");
  const [clientIndustry, setClientIndustry] = useState("");
  const [engagementTitle, setEngagementTitle] = useState("");
  const [challengeSummary, setChallengeSummary] = useState("");
  const [docText, setDocText] = useState(parsedDocument?.text ?? "");

  // Metrics
  const [metrics, setMetrics] = useState<CaseStudyMetric[]>([
    { label: "", value: "", description: "" },
  ]);

  // Approach points
  const [approachPoints, setApproachPoints] = useState<string[]>(["", "", ""]);

  // Result
  const [result, setResult] = useState<GenerateResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setDocText(ev.target?.result as string);
    reader.readAsText(file);
  };

  const updateMetric = (i: number, field: keyof CaseStudyMetric, val: string) => {
    setMetrics((prev) => prev.map((m, j) => j === i ? { ...m, [field]: val } : m));
  };

  const updateApproach = (i: number, val: string) => {
    setApproachPoints((prev) => prev.map((p, j) => j === i ? val : p));
  };

  const handleGenerate = async () => {
    if (!clientName.trim() || !engagementTitle.trim() || !docText.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const validMetrics = metrics.filter((m) => m.label.trim() && m.value.trim());
      const validApproach = approachPoints.filter((p) => p.trim());
      const res = await generateCaseStudy(
        {
          client_name: clientName.trim(),
          client_industry: clientIndustry,
          engagement_title: engagementTitle.trim(),
          source_document: {
            title: engagementTitle.trim(),
            text: docText,
            sections: [],
          },
          challenge_summary: challengeSummary.trim(),
          headline_metrics: validMetrics,
          our_approach_points: validApproach,
          project_id: projectId ?? null,
          llm_provider: llmProvider,
          llm_model: llmModel || null,
        },
        { token },
      );
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!result) return;
    setDownloading(true);
    try {
      await downloadArtifact(result.download_url, result.artifact_name, { token });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed.");
    } finally {
      setDownloading(false);
    }
  };

  const canGenerate = clientName.trim().length > 0 && engagementTitle.trim().length > 0 && docText.trim().length > 0;

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <BookMarked size={20} color="var(--bsbi-red)" style={{ marginRight: 8 }} />
          Case Study Generator
        </h1>
        <p className="page-subtitle">
          Turn a project document or delivery report into a professional, branded case study ready to share with clients.
        </p>
      </div>

      <div className="validate-layout">

        {/* ── LEFT: Inputs ── */}
        <div className="validate-input-col">

          {/* Client & Engagement */}
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 className="card-title">Client & Engagement</h3>

            <label className="form-label">Client Name *</label>
            <input
              className="form-control"
              style={{ marginBottom: 10 }}
              placeholder="e.g. Meridian Housing Association"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
            />

            <label className="form-label">Industry</label>
            <select
              className="form-control"
              style={{ marginBottom: 10 }}
              value={clientIndustry}
              onChange={(e) => setClientIndustry(e.target.value)}
            >
              <option value="">Select industry…</option>
              {INDUSTRY_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>

            <label className="form-label">Engagement Title *</label>
            <input
              className="form-control"
              style={{ marginBottom: 10 }}
              placeholder="e.g. Digital Transformation Programme"
              value={engagementTitle}
              onChange={(e) => setEngagementTitle(e.target.value)}
            />

            <label className="form-label">Challenge Summary (optional)</label>
            <textarea
              className="form-control"
              rows={3}
              placeholder="Briefly describe the client's problem — or leave blank and the AI will derive it from the source document."
              value={challengeSummary}
              onChange={(e) => setChallengeSummary(e.target.value)}
            />
          </div>

          {/* Headline Metrics */}
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 className="card-title">Headline Metrics</h3>
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 10 }}>
              These appear as large stat blocks in the document (e.g. "25% Cost Reduction"). Up to 4.
            </p>
            {metrics.map((m, i) => (
              <div key={i} style={{ display: "flex", gap: 6, marginBottom: 8, alignItems: "flex-start" }}>
                <input
                  className="form-control"
                  placeholder="Value (e.g. 25%)"
                  value={m.value}
                  onChange={(e) => updateMetric(i, "value", e.target.value)}
                  style={{ flex: "0 0 90px" }}
                />
                <input
                  className="form-control"
                  placeholder="Label (e.g. Cost Reduction)"
                  value={m.label}
                  onChange={(e) => updateMetric(i, "label", e.target.value)}
                  style={{ flex: 1 }}
                />
                <input
                  className="form-control"
                  placeholder="Sub-label (optional)"
                  value={m.description}
                  onChange={(e) => updateMetric(i, "description", e.target.value)}
                  style={{ flex: 1 }}
                />
                {metrics.length > 1 && (
                  <button
                    type="button"
                    style={{ background: "none", border: "none", cursor: "pointer", color: "var(--status-fail)", paddingTop: 8 }}
                    onClick={() => setMetrics((prev) => prev.filter((_, j) => j !== i))}
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            ))}
            {metrics.length < 4 && (
              <button
                type="button"
                className="btn btn-secondary"
                style={{ width: "100%", fontSize: 12 }}
                onClick={() => setMetrics((prev) => [...prev, { label: "", value: "", description: "" }])}
              >
                <Plus size={12} /> Add Metric
              </button>
            )}
          </div>

          {/* Approach Points */}
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 className="card-title">Key Approach Points (optional)</h3>
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 10 }}>
              These become numbered steps in the Our Approach section. Leave blank to let the AI write them.
            </p>
            {approachPoints.map((p, i) => (
              <div key={i} style={{ display: "flex", gap: 6, marginBottom: 6 }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: "var(--bsbi-red)", paddingTop: 8, minWidth: 22 }}>{String(i + 1).padStart(2, "0")}</span>
                <input
                  className="form-control"
                  placeholder={`Approach step ${i + 1}…`}
                  value={p}
                  onChange={(e) => updateApproach(i, e.target.value)}
                />
                {approachPoints.length > 1 && (
                  <button
                    type="button"
                    style={{ background: "none", border: "none", cursor: "pointer", color: "var(--status-fail)" }}
                    onClick={() => setApproachPoints((prev) => prev.filter((_, j) => j !== i))}
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
            ))}
            {approachPoints.length < 6 && (
              <button
                type="button"
                className="btn btn-secondary"
                style={{ width: "100%", fontSize: 12, marginTop: 4 }}
                onClick={() => setApproachPoints((prev) => [...prev, ""])}
              >
                <Plus size={12} /> Add Step
              </button>
            )}
          </div>

          {/* Source Document */}
          <div className="card">
            <h3 className="card-title">Source Document *</h3>
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8 }}>
              Paste a project brief, delivery report, programme document, or SOW. The AI will extract the narrative from it.
            </p>
            <label className="form-label">
              Document Text
              <label style={{ marginLeft: 8, cursor: "pointer", color: "var(--bsbi-red)", fontSize: 12 }}>
                ↑ Upload .txt file
                <input type="file" accept=".txt,.md" style={{ display: "none" }} onChange={handleFileUpload} />
              </label>
            </label>
            <textarea
              className="form-control validate-textarea"
              rows={12}
              placeholder="Paste project document text here…"
              value={docText}
              onChange={(e) => setDocText(e.target.value)}
            />

            {error && (
              <div className="message error" style={{ marginTop: 10 }}>
                <AlertCircle size={14} /> {error}
              </div>
            )}

            <button
              type="button"
              className="btn btn-primary"
              style={{ width: "100%", marginTop: 12 }}
              onClick={() => void handleGenerate()}
              disabled={loading || !canGenerate}
            >
              {loading
                ? <><Loader2 size={14} className="spin" /> Generating Case Study…</>
                : <><BookMarked size={14} /> Generate Case Study</>}
            </button>
          </div>
        </div>

        {/* ── RIGHT: Preview / Result ── */}
        <div className="validate-results-col">
          {!result && !loading && (
            <div className="validate-empty">
              <BookMarked size={40} strokeWidth={1.2} />
              <h2>No case study yet</h2>
              <p>Fill in the client details, add your headline metrics, paste the source document, and click Generate.</p>
            </div>
          )}

          {loading && (
            <div className="validate-empty">
              <Loader2 size={36} className="spin" />
              <h2>Writing your case study…</h2>
              <p>The AI is turning your source document into a professional narrative.</p>
            </div>
          )}

          {result && (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

              {/* Download banner */}
              <div className="card validate-verdict-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div className="verdict-badge verdict-pass" style={{ marginBottom: 6 }}>Case Study Ready</div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{result.artifact_name}</div>
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => void handleDownload()}
                  disabled={downloading}
                >
                  {downloading ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
                  Download DOCX
                </button>
              </div>

              {/* Section previews */}
              {result.sections.map((section, i) => (
                <div className="card" key={i}>
                  <h3 className="card-title" style={{ color: "var(--bsbi-red)" }}>{section.title}</h3>
                  {section.paragraphs.map((p, pi) => (
                    <p key={pi} style={{ fontSize: 13, lineHeight: 1.6, marginBottom: 8, color: "var(--text-primary)" }}>{p}</p>
                  ))}
                  {section.bullets.length > 0 && (
                    <ul style={{ paddingLeft: 20, margin: 0 }}>
                      {section.bullets.map((b, bi) => (
                        <li key={bi} style={{ fontSize: 13, lineHeight: 1.6, marginBottom: 4, color: "var(--text-primary)" }}>{b}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CaseStudyView;