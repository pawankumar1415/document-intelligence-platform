import { AlertCircle, Loader2 } from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { useAppState } from "../context/AppStateContext";
import { login, register } from "../services/api";

const LoginView = () => {
  const navigate = useNavigate();
  const { setSession, token } = useAppState();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (token) return <Navigate to="/studio" replace />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response =
        mode === "login"
          ? await login(email.trim(), password)
          : await register(email.trim(), password);
      setSession(response.access_token, response.user);
      navigate("/studio", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen">
      {/* Left — branding panel */}
      <div className="login-brand-panel">
        <div className="login-brand-content">
          <img src="/bsbi-logo.jpeg" alt="BSBI" className="login-brand-logo" />
          <h1 className="login-brand-title">Document Intelligence Platform</h1>
          <p className="login-brand-tagline">
            Transform raw project documents into polished Statements of Work and executive
            presentations — powered by AI.
          </p>
          <ul className="login-feature-list">
            <li><span className="login-feature-dot" />Multi-format parsing: .docx, .txt, .pdf with OCR</li>
            <li><span className="login-feature-dot" />LLM-powered SOW &amp; presentation generation</li>
            <li><span className="login-feature-dot" />Semantic search with pgvector embeddings</li>
            <li><span className="login-feature-dot" />Fully branded BSBI output templates</li>
          </ul>
        </div>
        <p className="login-brand-footer">BSBI Consultancy Solutions · Document Intelligence</p>
      </div>

      {/* Right — auth form */}
      <div className="login-form-panel">
        <article className="login-card">
          <div className="login-card-header">
            <h2>{mode === "login" ? "Welcome back" : "Create account"}</h2>
            <p>{mode === "login" ? "Sign in to your workspace" : "Get started in seconds"}</p>
          </div>

          <div className="auth-mode">
            <button
              className={`mode-btn${mode === "login" ? " active" : ""}`}
              type="button"
              onClick={() => { setMode("login"); setError(null); }}
            >
              Sign In
            </button>
            <button
              className={`mode-btn${mode === "register" ? " active" : ""}`}
              type="button"
              onClick={() => { setMode("register"); setError(null); }}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} className="login-form">
            <label>
              Email address
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                autoComplete="email"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 8 characters"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
            </label>
            <button className="btn btn-primary login-submit" type="submit" disabled={loading}>
              {loading
                ? <><Loader2 size={15} className="spin" /> Processing…</>
                : mode === "login" ? "Sign In" : "Create Account"
              }
            </button>
          </form>

          {error && (
            <div className="message error" style={{ marginTop: "16px" }}>
              <AlertCircle size={15} />
              <span>{error}</span>
            </div>
          )}

          {mode === "register" && (
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", textAlign: "center", marginTop: "14px" }}>
              The first registered account is automatically granted admin access.
            </p>
          )}
        </article>
      </div>
    </div>
  );
};

export default LoginView;