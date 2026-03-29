import { AlertCircle, Loader2, Shield, Trash2, UserCheck, UserX } from "lucide-react";
import { useEffect, useState } from "react";

import { useAppState } from "../context/AppStateContext";
import { ApiError } from "../services/api";

type UserRecord = {
  id: number;
  email: string;
  created_at: string;
  is_active?: boolean;
  is_admin?: boolean;
};

const AdminView = () => {
  const { token } = useAppState();
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/admin/users", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const text = await response.text();
        throw new ApiError(response.status, text);
      }
      const data = (await response.json()) as UserRecord[];
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleToggleActive = async (user: UserRecord) => {
    const key = `${user.id}-active`;
    setActionLoading(key);
    try {
      const response = await fetch(`/api/v1/admin/users/${user.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_active: !user.is_active }),
      });
      if (!response.ok) throw new Error("Update failed.");
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (user: UserRecord) => {
    if (!confirm(`Delete user "${user.email}" and all their data? This cannot be undone.`)) return;
    const key = `${user.id}-delete`;
    setActionLoading(key);
    try {
      const response = await fetch(`/api/v1/admin/users/${user.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("Delete failed.");
      await fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div>
          <h1 className="page-title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Shield size={22} color="var(--bsbi-red)" />
            User Management
          </h1>
          <p className="page-subtitle">Manage platform users, active status, and access control.</p>
        </div>
      </div>

      {error && (
        <div className="message error">
          <AlertCircle size={15} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-muted)", padding: "24px 0" }}>
          <Loader2 size={16} className="spin" />
          Loading users…
        </div>
      ) : users.length === 0 ? (
        <div className="card" style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          <p>No users found.</p>
        </div>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Joined</th>
                <th style={{ textAlign: "center" }}>Status</th>
                <th style={{ textAlign: "center" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} style={{ opacity: u.is_active === false ? 0.55 : 1 }}>
                  <td>
                    <span style={{ fontWeight: 500 }}>{u.email}</span>
                    {u.is_admin && <span className="admin-badge-admin">Admin</span>}
                  </td>
                  <td style={{ color: "var(--text-muted)" }}>
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                  </td>
                  <td style={{ textAlign: "center" }}>
                    <button
                      className={`admin-toggle-btn ${u.is_active !== false ? "on" : "off"}`}
                      onClick={() => handleToggleActive(u)}
                      disabled={!!actionLoading}
                      title={u.is_active !== false ? "Deactivate user" : "Activate user"}
                    >
                      {u.is_active !== false
                        ? <><UserCheck size={13} /> Active</>
                        : <><UserX size={13} /> Inactive</>
                      }
                    </button>
                  </td>
                  <td style={{ textAlign: "center" }}>
                    <button
                      className="admin-delete-btn"
                      onClick={() => handleDelete(u)}
                      disabled={!!actionLoading}
                      title="Delete user and all data"
                    >
                      <Trash2 size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p style={{ marginTop: "16px", fontSize: "0.75rem", color: "var(--text-muted)" }}>
        Note: Admin endpoints require a corresponding backend implementation. User management APIs will be wired in a future update.
      </p>
    </div>
  );
};

export default AdminView;