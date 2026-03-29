import { LayoutDashboard, Library, LogOut, Settings, Shield } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAppState } from "../context/AppStateContext";

const Sidebar = () => {
  const { user, clearSession } = useAppState();
  const navigate = useNavigate();

  const handleLogout = () => {
    clearSession();
    navigate("/login", { replace: true });
  };

  const initials = user?.email ? user.email.slice(0, 2).toUpperCase() : "?";

  return (
    <aside className="sidebar">
      {/* Brand header */}
      <div className="sidebar-header">
        <img src="/bsbi-logo.jpeg" alt="BSBI" className="sidebar-logo" />
        <div className="sidebar-brand">
          <span className="sidebar-brand-name">BSBI Intelligence</span>
          <span className="sidebar-brand-sub">Document Platform</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="nav-links">
        <span className="nav-section-label">Workspace</span>

        <NavLink
          to="/studio"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <LayoutDashboard size={16} />
          Studio
        </NavLink>

        <NavLink
          to="/outputs"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <Library size={16} />
          Output Library
        </NavLink>

        <span className="nav-section-label">Configuration</span>

        <NavLink
          to="/settings"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <Settings size={16} />
          AI Settings
        </NavLink>

        <NavLink
          to="/admin"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <Shield size={16} />
          Admin
        </NavLink>
      </nav>

      {/* User + logout */}
      <div className="sidebar-footer">
        {user && (
          <div className="sidebar-user">
            <div className="sidebar-avatar">{initials}</div>
            <div className="sidebar-user-info">
              <div className="sidebar-user-email">{user.email}</div>
            </div>
          </div>
        )}
        <button className="sidebar-logout-btn" type="button" onClick={handleLogout}>
          <LogOut size={14} />
          Sign Out
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;