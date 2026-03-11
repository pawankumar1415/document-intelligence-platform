import { AlertCircle, Lock, Mail } from "lucide-react";
import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { useAppState } from "../context/AppStateContext";
import { login, register } from "../services/api";


const LoginPage = () => {
  const navigate = useNavigate();
  const { setSession, token } = useAppState();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (token) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response =
        mode === "login" ? await login(email.trim(), password) : await register(email.trim(), password);
      setSession(response.access_token, response.user);
      navigate("/dashboard", { replace: true });
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Authentication failed.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="login-screen">
      <article className="login-card">
        <img src="/bsbi-logo.jpeg" alt="BSBI logo" className="login-logo" />
        <h1>BSBI Document Intelligence</h1>
        <p>Sign In</p>

        <div className="auth-mode">
          <button
            className={mode === "login" ? "mode-btn active" : "mode-btn"}
            type="button"
            onClick={() => setMode("login")}
          >
            Login
          </button>
          <button
            className={mode === "register" ? "mode-btn active" : "mode-btn"}
            type="button"
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <label>
            <Mail size={16} /> Email
            <input
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@company.com"
            />
          </label>
          <label>
            <Lock size={16} /> Password
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Minimum 8 characters"
            />
          </label>
          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? "Processing..." : mode === "login" ? "Login" : "Create Account"}
          </button>
        </form>

        {error && (
          <div className="message error">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
      </article>
    </section>
  );
};

export default LoginPage;
