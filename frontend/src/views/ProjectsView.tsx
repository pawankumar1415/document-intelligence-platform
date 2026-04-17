import { AlertCircle, BookOpen, FileText, FolderOpen, Layers, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAppState } from "../context/AppStateContext";
import { createProject, listProjects } from "../services/api";
import type { ProjectResponse } from "../types/app";

const ProjectsView = () => {
  const { token } = useAppState();
  const navigate = useNavigate();

  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listProjects({ token });
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects.");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const project = await createProject({ name: newName.trim() }, { token });
      setProjects((prev) => [project, ...prev]);
      setNewName("");
      setShowCreate(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project.");
    } finally {
      setCreating(false);
    }
  };

  const fmtDate = (iso: string) =>
    new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <h1 className="page-title">Projects</h1>
          <p className="page-subtitle">
            Engagement workspaces — each project groups its documents, artifacts, validations and clauses.
          </p>
        </div>
        <button
          className="btn btn-primary"
          type="button"
          onClick={() => setShowCreate((v) => !v)}
          style={{ flexShrink: 0 }}
        >
          {showCreate ? <X size={14} /> : <Plus size={14} />}
          {showCreate ? "Cancel" : "New Project"}
        </button>
      </div>

      {showCreate && (
        <div className="card" style={{ marginBottom: "20px", padding: "20px" }}>
          <h3 style={{ margin: "0 0 12px", fontSize: "0.95rem", fontWeight: 600 }}>Create Project</h3>
          <form onSubmit={handleCreate} style={{ display: "flex", gap: "10px" }}>
            <input
              className="form-input"
              type="text"
              placeholder="Project / engagement name…"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              style={{ flex: 1 }}
              autoFocus
            />
            <button className="btn btn-primary" type="submit" disabled={creating || !newName.trim()}>
              {creating ? "Creating…" : "Create"}
            </button>
          </form>
        </div>
      )}

      {error && (
        <div className="message error" style={{ marginBottom: "16px" }}>
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="card" style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Loading projects…
        </div>
      ) : projects.length === 0 ? (
        <div className="card library-empty">
          <FolderOpen size={38} strokeWidth={1.3} />
          <h2>No projects yet</h2>
          <p>Create a project to group an engagement's documents and outputs in one workspace.</p>
        </div>
      ) : (
        <div className="library-grid">
          {projects.map((project) => (
            <article
              key={project.id}
              className="card library-card"
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/projects/${project.id}`)}
            >
              <div className="library-card-top">
                <div className="library-card-icon badge-sow">
                  <FolderOpen size={18} />
                </div>
              </div>

              <h3 className="library-card-title">{project.name}</h3>

              <div className="library-card-meta">
                <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <FileText size={11} /> Created {fmtDate(project.created_at)}
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <Layers size={11} /> Updated {fmtDate(project.updated_at)}
                </span>
              </div>

              <button
                className="btn btn-secondary"
                type="button"
                onClick={(e) => { e.stopPropagation(); navigate(`/projects/${project.id}`); }}
                style={{ marginTop: "auto" }}
              >
                <BookOpen size={13} />
                Open Workspace
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProjectsView;