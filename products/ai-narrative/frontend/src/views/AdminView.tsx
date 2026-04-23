import { AlertCircle, Loader2, Shield, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useAppState } from "../context/AppStateContext";
import { adminDeleteUser, adminListUsers, adminUpdateUser } from "../services/api";
import type { AdminUserRecord } from "../types/app";

export default function AdminView() {
  const { token, user } = useAppState();
  const [users, setUsers] = useState<AdminUserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadUsers = async () => {
    setLoading(true);
    try {
      setUsers(await adminListUsers({ token }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadUsers(); }, [token]);

  const toggleAdmin = async (u: AdminUserRecord) => {
    try {
      const updated = await adminUpdateUser(u.id, { is_admin: !u.is_admin }, { token });
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed.");
    }
  };

  const toggleActive = async (u: AdminUserRecord) => {
    try {
      const updated = await adminUpdateUser(u.id, { is_active: !u.is_active }, { token });
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed.");
    }
  };

  const handleDelete = async (u: AdminUserRecord) => {
    if (!confirm(`Delete user "${u.email}"? All their data will be removed.`)) return;
    try {
      await adminDeleteUser(u.id, { token });
      setUsers((prev) => prev.filter((x) => x.id !== u.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title"><Shield size={20} color="var(--bsbi-red)" /> Admin Panel</h1>
        <p className="page-subtitle">Manage user accounts and permissions.</p>
      </div>

      {error && (
        <div className="message error" style={{ marginBottom: 16 }}>
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {loading ? (
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Loader2 size={16} className="spin" /> Loading users…
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="admin-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Scores</th>
                <th>Since</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td style={{ fontWeight: 500 }}>{u.email}</td>
                  <td>
                    <span className={`badge ${u.is_admin ? "badge-admin" : "badge-user"}`}>
                      {u.is_admin ? "Admin" : "User"}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${u.is_active ? "badge-active" : "badge-inactive"}`}>
                      {u.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td style={{ textAlign: "center" }}>{u.score_count}</td>
                  <td style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                    {new Date(u.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    {u.id !== user?.id && (
                      <div style={{ display: "flex", gap: 6 }}>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ padding: "4px 10px", fontSize: "0.78rem" }}
                          onClick={() => void toggleAdmin(u)}
                        >
                          {u.is_admin ? "Demote" : "Promote"}
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ padding: "4px 10px", fontSize: "0.78rem" }}
                          onClick={() => void toggleActive(u)}
                        >
                          {u.is_active ? "Deactivate" : "Activate"}
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger"
                          style={{ padding: "4px 8px" }}
                          onClick={() => void handleDelete(u)}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    )}
                    {u.id === user?.id && (
                      <span style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>You</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}