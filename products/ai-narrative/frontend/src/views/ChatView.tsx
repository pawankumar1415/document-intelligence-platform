import {
  AlertCircle,
  BookOpen,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Loader2,
  MessageSquare,
  Paperclip,
  Send,
  User,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ModelControlBar from "../components/ModelControlBar";
import { useAppState } from "../context/AppStateContext";
import { getDomainProfile, getReferencePeriods, ingestReference, sendChatMessage } from "../services/api";
import type { ChatMessage, ChatSource, DomainProfile, LLMProvider } from "../types/app";

const DEFAULT_SUGGESTED_QUESTIONS = [
  "Which projects have issues this period?",
  "Summarise the overall status across all projects.",
  "Which projects are at risk of missing their milestones?",
  "What are the key risks mentioned across narratives?",
  "Highlight any projects that have changed status recently.",
];

interface UIMessage extends ChatMessage {
  sources?: ChatSource[];
}

function SourcesPanel({ sources }: { sources: ChatSource[] }) {
  const [open, setOpen] = useState(false);
  if (sources.length === 0) return null;
  return (
    <div style={{ marginTop: 8 }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{
          background: "none", border: "none", cursor: "pointer", padding: 0,
          display: "flex", alignItems: "center", gap: 4,
          fontSize: "0.73rem", color: "var(--text-muted)", fontWeight: 600,
        }}
      >
        <BookOpen size={11} />
        {sources.length} source{sources.length !== 1 ? "s" : ""} used
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>
      {open && (
        <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 6 }}>
          {sources.map((s, i) => (
            <div
              key={i}
              style={{
                background: "var(--bg-tertiary)", border: "1px solid var(--border-color)",
                borderRadius: 6, padding: "8px 10px", fontSize: "0.75rem",
              }}
            >
              <div style={{ fontWeight: 700, marginBottom: 3, color: "var(--text-primary)" }}>
                {s.unique_id}
                <span style={{ marginLeft: 6, fontWeight: 400, color: "var(--text-muted)" }}>
                  similarity {(s.score * 100).toFixed(0)}%
                </span>
              </div>
              <div style={{ color: "var(--text-secondary)", lineHeight: 1.5 }}>
                {s.excerpt}…
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ChatView() {
  const { token, llmProvider, llmModel, setProvider } = useAppState();

  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [input, setInput] = useState("");
  const [period, setPeriod] = useState("Any period");
  const [periodOptions, setPeriodOptions] = useState<string[]>(["Any period"]);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>(DEFAULT_SUGGESTED_QUESTIONS);
  const [domainProfile, setDomainProfile] = useState<DomainProfile | null>(null);
  const [provider, setLocalProvider] = useState<LLMProvider>(llmProvider);
  const [model, setModel] = useState<string | null>(llmModel);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [topK, setTopK] = useState(6);

  const [uploadStatus, setUploadStatus] = useState<
    { state: "idle" } | { state: "loading"; name: string } | { state: "done"; name: string; count: number } | { state: "error"; name: string; message: string }
  >({ state: "idle" });

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([
      getReferencePeriods({ token }),
      getDomainProfile({ token }),
    ]).then(([{ periods }, profile]) => {
      if (periods.length > 0) setPeriodOptions(["Any period", ...periods]);
      if (profile && profile.domain_name) {
        setDomainProfile(profile);
        if (profile.suggested_questions?.length > 0) {
          setSuggestedQuestions(profile.suggested_questions);
        }
      }
    }).catch(() => {});
  }, [token]);

  useEffect(() => {
    setLocalProvider(llmProvider);
    setModel(llmModel);
  }, [llmProvider, llmModel]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleProviderChange = (p: LLMProvider, m: string | null) => {
    setLocalProvider(p);
    setModel(m);
    setProvider(p, m);
  };

  const buildQuery = (text: string): string => {
    if (period === "Any period") return text;
    return `[${period}] ${text}`;
  };

  const handleSend = async (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || loading) return;

    const userMsg: UIMessage = { role: "user", content: buildQuery(content) };
    const history = [...messages, userMsg];
    setMessages(history);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await sendChatMessage(
        {
          messages: history.map((m) => ({ role: m.role, content: m.content })),
          provider,
          model: model ?? undefined,
          top_k: topK,
        },
        { token }
      );
      setMessages([
        ...history,
        { role: "assistant", content: res.reply, sources: res.sources },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed.");
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setError(null);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setUploadStatus({ state: "loading", name: file.name });
    try {
      const res = await ingestReference(file, { token });
      setUploadStatus({ state: "done", name: file.name, count: res.record_count });
    } catch (err) {
      setUploadStatus({
        state: "error",
        name: file.name,
        message: err instanceof Error ? err.message : "Upload failed.",
      });
    }
  };

  return (
    <div className="page-container" style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden", padding: "24px 28px", boxSizing: "border-box" }}>
      <div className="page-header" style={{ flexShrink: 0, marginBottom: 16 }}>
        <h1 className="page-title">
          <MessageSquare size={20} color="var(--bsbi-red)" /> Knowledge Base Chat
        </h1>
        <p className="page-subtitle">
          Ask questions about your uploaded reference narratives. The assistant uses your library to answer.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "250px 1fr", gap: 16, flex: 1, minHeight: 0, overflow: "hidden" }}>

        {/* LEFT: Controls — scrollable independently */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, overflowY: "auto", paddingRight: 4 }}>
          <div className="card">
            <h3 className="card-title">Settings</h3>

            <label className="form-label">Period filter</label>
            <select
              className="form-control"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              style={{ marginBottom: 12 }}
            >
              {periodOptions.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginBottom: 14 }}>
              Prefixes your question with the selected period so the AI focuses on that reporting interval.
            </div>

            <label className="form-label">Reference depth (top-k)</label>
            <input
              className="form-control"
              type="number" min={1} max={20} value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              style={{ marginBottom: 14 }}
            />

            <ModelControlBar provider={provider} model={model} onChange={handleProviderChange} />

            {provider === "ollama" && model && /0\.[0-9]b/i.test(model) && (
              <div style={{
                marginTop: 10, padding: "8px 10px", borderRadius: 6,
                background: "#fff8e1", border: "1px solid #f59e0b",
                fontSize: "0.72rem", color: "#92400e", lineHeight: 1.5,
              }}>
                ⚠ Small models (&lt;1B) often ignore document context. Switch to <strong>Groq → llama-3.3-70b-versatile</strong> for reliable answers.
              </div>
            )}
          </div>

          <div className="card">
            <h3 className="card-title">Suggested questions</h3>
            {domainProfile?.domain_name && (
              <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginBottom: 8, fontStyle: "italic" }}>
                Tailored for: {domainProfile.domain_name}
              </div>
            )}
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {suggestedQuestions.map((q) => (
                <button
                  key={q}
                  type="button"
                  disabled={loading}
                  onClick={() => void handleSend(q)}
                  style={{
                    textAlign: "left", background: "var(--bg-secondary)",
                    border: "1px solid var(--border-color)", borderRadius: 6,
                    padding: "7px 10px", fontSize: "0.78rem", cursor: "pointer",
                    color: "var(--text-secondary)", lineHeight: 1.4,
                    transition: "border-color 0.15s",
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {messages.length > 0 && (
            <button type="button" className="btn btn-secondary" onClick={clearChat} style={{ justifyContent: "center" }}>
              Clear chat
            </button>
          )}
        </div>

        {/* RIGHT: Chat window */}
        <div style={{ display: "flex", flexDirection: "column", minHeight: 0, height: "100%", overflow: "hidden" }}>

          {/* Message list */}
          <div
            style={{
              flex: 1, overflowY: "auto", padding: "4px 0 16px",
              display: "flex", flexDirection: "column", gap: 16,
            }}
          >
            {messages.length === 0 && !loading && (
              <div className="score-empty" style={{ marginTop: 40 }}>
                <Bot size={40} strokeWidth={1.2} />
                <h2>Ask your knowledge base</h2>
                <p>
                  Questions are answered using your uploaded reference narratives.<br />
                  Select a period filter or pick a suggested question to start.
                </p>
                {periodOptions.length <= 1 && (
                  <div style={{
                    marginTop: 16, padding: "10px 16px", borderRadius: 8,
                    background: "var(--bg-tertiary)", border: "1px solid var(--border-color)",
                    fontSize: "0.8rem", color: "var(--text-muted)", maxWidth: 420,
                  }}>
                    No reference narratives detected in your library yet.{" "}
                    <a href="/references" style={{ color: "var(--bsbi-red)", fontWeight: 600 }}>
                      Upload files to Reference Library
                    </a>{" "}
                    first so the AI has content to answer from.
                  </div>
                )}
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  flexDirection: msg.role === "user" ? "row-reverse" : "row",
                  gap: 10, alignItems: "flex-start",
                }}
              >
                <div
                  style={{
                    width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
                    background: msg.role === "user" ? "var(--bsbi-red)" : "var(--bg-tertiary)",
                    border: "1px solid var(--border-color)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}
                >
                  {msg.role === "user"
                    ? <User size={14} color="#fff" />
                    : <Bot size={14} color="var(--bsbi-red)" />}
                </div>
                <div style={{ maxWidth: "78%" }}>
                  <div
                    style={{
                      background: msg.role === "user" ? "var(--bsbi-red)" : "var(--bg-primary)",
                      color: msg.role === "user" ? "#fff" : "var(--text-primary)",
                      border: msg.role === "user" ? "none" : "1px solid var(--border-color)",
                      borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                      padding: "10px 14px",
                      fontSize: "0.85rem",
                      lineHeight: 1.6,
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {msg.content}
                  </div>
                  {msg.role === "assistant" && msg.sources && (
                    <SourcesPanel sources={msg.sources} />
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <div
                  style={{
                    width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
                    background: "var(--bg-tertiary)", border: "1px solid var(--border-color)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}
                >
                  <Bot size={14} color="var(--bsbi-red)" />
                </div>
                <div
                  style={{
                    background: "var(--bg-primary)", border: "1px solid var(--border-color)",
                    borderRadius: "14px 14px 14px 4px", padding: "10px 14px",
                    display: "flex", alignItems: "center", gap: 8, fontSize: "0.85rem",
                    color: "var(--text-muted)",
                  }}
                >
                  <Loader2 size={14} className="spin" /> Thinking…
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div style={{ flexShrink: 0, paddingTop: 12, borderTop: "1px solid var(--border-color)" }}>
            {error && (
              <div className="message error" style={{ marginBottom: 8, fontSize: "0.8rem" }}>
                <AlertCircle size={13} /> {error}
              </div>
            )}

            {/* File upload status badge */}
            {uploadStatus.state !== "idle" && (
              <div style={{
                display: "flex", alignItems: "center", gap: 8, marginBottom: 8,
                padding: "6px 10px", borderRadius: 6, fontSize: "0.78rem",
                background: uploadStatus.state === "error" ? "#fef2f2" : uploadStatus.state === "done" ? "#f0fdf4" : "var(--bg-tertiary)",
                border: `1px solid ${uploadStatus.state === "error" ? "#fca5a5" : uploadStatus.state === "done" ? "#86efac" : "var(--border-color)"}`,
                color: uploadStatus.state === "error" ? "#b91c1c" : uploadStatus.state === "done" ? "#15803d" : "var(--text-secondary)",
              }}>
                {uploadStatus.state === "loading" && <Loader2 size={13} className="spin" />}
                {uploadStatus.state === "done" && <CheckCircle2 size={13} />}
                {uploadStatus.state === "error" && <AlertCircle size={13} />}
                <span style={{ flex: 1 }}>
                  {uploadStatus.state === "loading" && `Indexing ${uploadStatus.name}…`}
                  {uploadStatus.state === "done" && `${uploadStatus.name} — ${uploadStatus.count} record${uploadStatus.count !== 1 ? "s" : ""} indexed`}
                  {uploadStatus.state === "error" && `${uploadStatus.name}: ${uploadStatus.message}`}
                </span>
                <button
                  type="button"
                  onClick={() => setUploadStatus({ state: "idle" })}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: 0, display: "flex", color: "inherit", opacity: 0.6 }}
                >
                  <X size={13} />
                </button>
              </div>
            )}

            <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls,.csv,.docx,.pdf,.txt"
                style={{ display: "none" }}
                onChange={handleFileUpload}
              />
              <button
                type="button"
                title="Upload file to knowledge base"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadStatus.state === "loading"}
                style={{
                  background: "none", border: "1px solid var(--border-color)", borderRadius: 8,
                  cursor: "pointer", padding: "0 10px", alignSelf: "stretch",
                  color: "var(--text-muted)", display: "flex", alignItems: "center",
                  transition: "border-color 0.15s, color 0.15s",
                }}
              >
                <Paperclip size={16} />
              </button>
              <textarea
                ref={inputRef}
                className="form-control"
                rows={2}
                placeholder={
                  period !== "Any period"
                    ? `Ask about ${period} narratives… (Enter to send, Shift+Enter for new line)`
                    : "Ask about your reference narratives… (Enter to send)"
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                style={{ flex: 1, resize: "none", fontSize: "0.85rem" }}
              />
              <button
                type="button"
                className="btn btn-primary"
                style={{ padding: "10px 14px", alignSelf: "stretch" }}
                disabled={loading || !input.trim()}
                onClick={() => void handleSend()}
              >
                {loading ? <Loader2 size={15} className="spin" /> : <Send size={15} />}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}