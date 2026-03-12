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
  const { clearSession, user } = useAppState();

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
          <span className="mobile-provider-label">Model controls are available below the navigation bar.</span>
          <button className="logout-btn" type="button" onClick={handleLogout}>
            Logout
          </button>
        </nav>
      )}
    </header>
  );
};

export default Navbar;
