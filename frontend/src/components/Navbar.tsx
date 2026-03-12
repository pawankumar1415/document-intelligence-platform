import { Menu, X } from "lucide-react";
import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAppState } from "../context/AppStateContext";

const links = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/upload", label: "Upload" },
  { to: "/generate", label: "Generate" },
  { to: "/outputs", label: "Outputs" },
];

const navClassName = ({ isActive }: { isActive: boolean }) =>
  `top-nav-link${isActive ? " active" : ""}`;

const Navbar = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();
  const {
    clearSession,
    llmModel,
    llmProvider,
    providerCatalog,
    providerCatalogLoading,
    setLlmModel,
    setLlmProvider,
    user,
  } = useAppState();
  const providerOptions = providerCatalog.filter((entry) => entry.enabled);
  const activeProvider = providerOptions.find((entry) => entry.provider === llmProvider);
  const activeModels = activeProvider?.models ?? [];

  const handleLogout = () => {
    clearSession();
    navigate("/login", { replace: true });
  };

  return (
    <header className="top-nav">
      <div className="top-nav-inner">
        <NavLink className="brand" to="/dashboard" onClick={() => setMobileOpen(false)}>
          <img src="/bsbi-logo.jpeg" alt="BSBI logo" className="brand-logo" />
          <div className="brand-copy">
            <span className="brand-title">BSBI Intelligence Studio</span>
            <span className="brand-subtitle">Document Intelligence Platform</span>
          </div>
        </NavLink>

        <nav className="desktop-nav">
          {links.map((link) => (
            <NavLink key={link.to} to={link.to} className={navClassName}>
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="top-nav-controls">
          <select
            className="provider-select"
            value={llmProvider}
            onChange={(event) => setLlmProvider(event.target.value as "openai" | "groq" | "azure_openai")}
            title="LLM Provider"
            disabled={providerCatalogLoading || providerOptions.length === 0}
          >
            {providerOptions.length === 0 && <option value={llmProvider}>No providers</option>}
            {providerOptions.map((entry) => (
              <option key={entry.provider} value={entry.provider}>
                {entry.display_name}
              </option>
            ))}
          </select>
          <select
            className="provider-select model-select"
            value={llmModel}
            onChange={(event) => setLlmModel(llmProvider, event.target.value)}
            title="LLM Model"
            disabled={providerCatalogLoading || activeModels.length === 0}
          >
            {activeModels.length === 0 && <option value={llmModel || ""}>No models</option>}
            {activeModels.map((model) => (
              <option key={model.id} value={model.id}>
                {model.label}
              </option>
            ))}
          </select>
          <span className="user-chip">{user?.email}</span>
          <button className="logout-btn" type="button" onClick={handleLogout}>
            Logout
          </button>
        </div>

        <button
          className="mobile-toggle"
          type="button"
          onClick={() => setMobileOpen((open) => !open)}
          aria-label="Toggle navigation"
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {mobileOpen && (
        <nav className="mobile-nav">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={navClassName}
              onClick={() => setMobileOpen(false)}
            >
              {link.label}
            </NavLink>
          ))}
          <label className="mobile-provider-label">
            LLM Provider
            <select
              className="provider-select"
              value={llmProvider}
              onChange={(event) => setLlmProvider(event.target.value as "openai" | "groq" | "azure_openai")}
              disabled={providerCatalogLoading || providerOptions.length === 0}
            >
              {providerOptions.length === 0 && <option value={llmProvider}>No providers</option>}
              {providerOptions.map((entry) => (
                <option key={entry.provider} value={entry.provider}>
                  {entry.display_name}
                </option>
              ))}
            </select>
          </label>
          <label className="mobile-provider-label">
            LLM Model
            <select
              className="provider-select model-select"
              value={llmModel}
              onChange={(event) => setLlmModel(llmProvider, event.target.value)}
              disabled={providerCatalogLoading || activeModels.length === 0}
            >
              {activeModels.length === 0 && <option value={llmModel || ""}>No models</option>}
              {activeModels.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.label}
                </option>
              ))}
            </select>
          </label>
          <button className="logout-btn" type="button" onClick={handleLogout}>
            Logout
          </button>
        </nav>
      )}
    </header>
  );
};

export default Navbar;
