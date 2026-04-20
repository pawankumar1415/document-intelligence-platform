import { AlertCircle, Bot, Loader2, MessageSquare, Send, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { useAppState } from "../context/AppStateContext";
import { sendChatMessage } from "../services/api";
import type { ChatMessage } from "../types/app";

const ChatView = () => {
  const { token, llmProvider, llmModel, projectId } = useAppState();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const result = await sendChatMessage(
        {
          question,
          session_id: sessionId,
          project_id: projectId ?? null,
          llm_provider: llmProvider,
          llm_model: llmModel || null,
        },
        { token },
      );
      setSessionId(result.session_id);
      setMessages((prev) => [...prev, { role: "assistant", content: result.answer }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed.");
      // Remove the optimistically-added user message on failure
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  return (
    <div className="page-container chat-page">
      <div className="page-header">
        <h1 className="page-title">
          <MessageSquare size={20} color="var(--bsbi-red)" style={{ marginRight: 8 }} />
          Document Chat
        </h1>
        <p className="page-subtitle">
          Ask questions about your uploaded documents. The assistant retrieves relevant context automatically.
        </p>
      </div>

      {error && (
        <div className="message error" style={{ marginBottom: 12 }}>
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {/* Message thread */}
      <div className="chat-thread">
        {messages.length === 0 && !loading && (
          <div className="chat-empty">
            <Bot size={36} strokeWidth={1.3} />
            <h2>Start a conversation</h2>
            <p>Upload a document in Studio, then ask anything about its contents.</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble-row ${msg.role}`}>
            <div className="chat-avatar">
              {msg.role === "user" ? <User size={14} /> : <Bot size={14} />}
            </div>
            <div className="chat-bubble">
              <div className="chat-bubble-text chat-markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="chat-bubble-row assistant">
            <div className="chat-avatar">
              <Bot size={14} />
            </div>
            <div className="chat-bubble chat-bubble-typing">
              <Loader2 size={14} className="spin" />
              <span>Thinking…</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="chat-input-bar">
        <textarea
          ref={textareaRef}
          className="chat-input"
          rows={1}
          placeholder="Ask a question about your documents… (Enter to send, Shift+Enter for new line)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button
          className="btn btn-primary chat-send-btn"
          type="button"
          onClick={() => void handleSend()}
          disabled={loading || !input.trim()}
        >
          {loading ? <Loader2 size={15} className="spin" /> : <Send size={15} />}
        </button>
      </div>
    </div>
  );
};

export default ChatView;