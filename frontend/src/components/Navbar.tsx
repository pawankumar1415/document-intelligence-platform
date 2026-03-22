import { LayoutDashboard, Library, LogOut, Menu, X } from "lucide-react";
import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAppState } from "../context/AppStateContext";

const links = [
  { to: "/dashboard", label: "Studio", Icon: LayoutDashboard },
  { to: "/outputs", label: "Library", Icon: Library },
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

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : "??";

  return (
    <header className="top-nav">
      <div className="top-nav-inner">
        <NavLink className="brand" to="/dashboard" onClick={() => setMobileOpen(false)}>
          <img src="/bsbi-logo.jpeg" alt="BSBI" className="brand-logo" />
          <div className="brand-copy">
            <span className="brand-title">BSBI Intelligence</span>
            <span className="brand-subtitle">Document Intelligence Platform</span>
          </div>
        </NavLink>

        <nav className="desktop-nav">
          {links.map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} className={navClassName}>
              <Icon size={14} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="top-nav-controls">
          {user?.email && (
            <div className="user-chip">
              <span className="user-avatar">{initials}</span>
              <span className="user-email">{user.email}</span>
            </div>
          )}
          <button className="logout-btn" type="button" onClick={handleLogout} title="Sign out">
            <LogOut size={14} />
            <span>Logout</span>
          </button>
        </div>

        <button
          className="mobile-toggle"
          type="button"
          onClick={() => setMobileOpen((o) => !o)}
          aria-label="Toggle navigation"
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {mobileOpen && (
        <nav className="mobile-nav">
          {links.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={navClassName}
              onClick={() => setMobileOpen(false)}
            >
              <Icon size={14} /> {label}
            </NavLink>
          ))}
          <button className="logout-btn mobile-logout" type="button" onClick={handleLogout}>
            <LogOut size={14} /> Logout
          </button>
        </nav>
      )}
    </header>
  );
};

export default Navbar;