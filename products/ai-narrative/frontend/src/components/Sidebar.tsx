import {
  BarChart3,
  BookMarked,
  BookOpen,
  Layers,
  LogOut,
  MessageSquare,
  Settings,
  Shield,
  Sparkles,
} from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAppState } from "../context/AppStateContext";

const navItems = [
  { to: "/score",      label: "Score Narrative",    icon: <Sparkles size={16} />,      section: "SCORING" },
  { to: "/batch",      label: "Batch Score",         icon: <Layers size={16} />,        section: null },
  { to: "/references", label: "Reference Library",   icon: <BookOpen size={16} />,      section: "DATA" },
  { to: "/chat",       label: "Knowledge Base Chat", icon: <MessageSquare size={16} />, section: null },
  { to: "/analytics",  label: "Analytics",           icon: <BarChart3 size={16} />,     section: "INSIGHTS" },
  { to: "/docs",       label: "Documentation",       icon: <BookMarked size={16} />,    section: "HELP" },
  { to: "/settings",   label: "Settings",            icon: <Settings size={16} />,      section: "SYSTEM" },
  { to: "/admin",      label: "Admin",               icon: <Shield size={16} />,        section: null },
];

export default function Sidebar() {
  const { user, clearSession } = useAppState();
  const navigate = useNavigate();

  const handleLogout = () => {
    clearSession();
    navigate("/login");
  };

  let lastSection: string | null = null;

  return (
    <nav className="sidebar">
      {/* Dual logos */}
      <div className="sidebar-logos">
        <img src="/logo-bsbi.jpeg" alt="BSBI Consulting" className="sidebar-logo" />
        <div className="sidebar-logo-divider" />
        <img src="/logo-data.jpeg" alt="Data Analytics" className="sidebar-logo" />
      </div>

      <div className="sidebar-product-name">AI Narrative Search</div>

      <div className="nav-links">
        {navItems.map((item) => {
          if (item.to === "/admin" && !user?.is_admin) return null;

          const showSection = item.section && item.section !== lastSection;
          if (item.section) lastSection = item.section;

          return (
            <div key={item.to}>
              {showSection && <div className="nav-section">{item.section}</div>}
              <NavLink
                to={item.to}
                className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
              >
                {item.icon}
                {item.label}
              </NavLink>
            </div>
          );
        })}
      </div>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-avatar">
            {(user?.email?.[0] ?? "U").toUpperCase()}
          </div>
          <div style={{ overflow: "hidden", flex: 1 }}>
            <div className="sidebar-user-email">{user?.email ?? "—"}</div>
            <div className="sidebar-user-role">{user?.is_admin ? "Administrator" : "User"}</div>
          </div>
        </div>
        <button type="button" className="sidebar-logout-btn" onClick={handleLogout}>
          <LogOut size={13} /> Sign Out
        </button>
      </div>
    </nav>
  );
}