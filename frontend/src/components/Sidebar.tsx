import { ArrowUpDown, BarChart2, BookMarked, BookOpen, ClipboardCheck, FolderOpen, LayoutDashboard, Layers, Library, LogOut, MessageSquare, Settings, Shield, Table2, Wand2 } from "lucide-react";
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
          to="/chat"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <MessageSquare size={16} />
          Document Chat
        </NavLink>

        <NavLink
          to="/outputs"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <Library size={16} />
          Output Library
        </NavLink>

        <NavLink
          to="/projects"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <FolderOpen size={16} />
          Projects
        </NavLink>

        <NavLink
          to="/templates"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <Wand2 size={16} />
          Templates
        </NavLink>

        <NavLink
          to="/compare"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <ArrowUpDown size={16} />
          Compare Docs
        </NavLink>

        <NavLink
          to="/extract"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <Table2 size={16} />
          Extract Data
        </NavLink>

        <NavLink
          to="/clauses"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <BookOpen size={16} />
          Clause Library
        </NavLink>

        <NavLink
          to="/case-study"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <BookMarked size={16} />
          Case Studies
        </NavLink>

        <span className="nav-section-label">Validation</span>

        <NavLink
          to="/validate"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <ClipboardCheck size={16} />
          Validate Document
        </NavLink>

        <NavLink
          to="/batch-validate"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <Layers size={16} />
          Batch Validation
        </NavLink>

        <span className="nav-section-label">Insights</span>

        <NavLink
          to="/analytics"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <BarChart2 size={16} />
          Analytics
        </NavLink>

        <span className="nav-section-label">Configuration</span>

        <NavLink
          to="/settings"
          className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
        >
          <Settings size={16} />
          AI Settings
        </NavLink>

        {user?.is_admin && (
          <NavLink
            to="/admin"
            className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
          >
            <Shield size={16} />
            Admin
          </NavLink>
        )}
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