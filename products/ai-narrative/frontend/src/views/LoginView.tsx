import { AlertCircle, Loader2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppStateContext";
import { login, register } from "../services/api";

export default function LoginView() {
  const { setSession } = useAppState();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = mode === "login"
        ? await login(email, password)
        : await register(email, password);
      setSession(resp.access_token, resp.user);
      navigate("/score");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen">
      {/* Left brand panel */}
      <div className="login-brand">
        <div className="login-brand-content">
          <div className="login-logos">
            <img src="/logo-bsbi.jpeg" alt="BSBI Consulting" className="login-logo" />
            <div className="login-logo-divider" />
            <img src="/logo-data.jpeg" alt="Data Analytics" className="login-logo" />
          </div>
          <h1 className="login-headline">
            AI Narrative<br />
            <span>Search</span>
          </h1>
          <p className="login-tagline">
            Score narrative text, detect abnormalities against reference data,
            and process batches with AI-powered quality analysis.
          </p>
          <ul className="login-features">
            <li>Score any narrative against custom rubrics</li>
            <li>Detect abnormalities vs reference corpus</li>
            <li>Single and batch Excel processing</li>
            <li>AI-suggested rewrites for failed narratives</li>
            <li>Full analytics dashboard</li>
          </ul>
        </div>
        <div style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.2)" }}>
          BSBI Consulting × Data Analytics
        </div>
      </div>

      {/* Right form panel */}
      <div className="login-form-panel">
        <h2 className="login-form-title">
          {mode === "login" ? "Sign in" : "Create account"}
        </h2>
        <p className="login-form-sub">
          {mode === "login"
            ? "Welcome back. Enter your credentials."
            : "Set up your AI Narrative Search account."}
        </p>

        <form onSubmit={(e) => void handleSubmit(e)}>
          <label className="form-label">Email address</label>
          <input
            className="form-control"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ marginBottom: 14 }}
            required
            autoFocus
          />

          <label className="form-label">Password</label>
          <input
            className="form-control"
            type="password"
            placeholder="Min. 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ marginBottom: 20 }}
            required
          />

          {error && (
            <div className="message error" style={{ marginBottom: 14 }}>
              <AlertCircle size={14} /> {error}
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", justifyContent: "center", padding: "10px" }}
            disabled={loading}
          >
            {loading
              ? <><Loader2 size={14} className="spin" /> {mode === "login" ? "Signing in…" : "Creating account…"}</>
              : mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>

        <div className="login-switch">
          {mode === "login" ? (
            <>Don't have an account? <button onClick={() => setMode("register")}>Sign up</button></>
          ) : (
            <>Already have an account? <button onClick={() => setMode("login")}>Sign in</button></>
          )}
        </div>
      </div>
    </div>
  );
}