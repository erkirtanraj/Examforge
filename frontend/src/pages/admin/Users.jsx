import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { PageHeader, DataTable, Pill, inputCls, errMsg } from "../../components/admin/kit";

const ROLES = ["student", "teacher", "support", "admin", "super_admin"];

export default function Users() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const load = () => api.get("/admin/users").then((r) => setUsers(r.data));
  useEffect(() => { load(); }, []);

  const changeRole = async (u, role) => {
    try {
      await api.put(`/admin/users/${u.id}/role`, { role });
      toast.success(`${u.name} is now ${role.replace("_", " ")}`);
      load();
    } catch (e) { toast.error(errMsg(e)); }
  };

  const rows = users.filter((u) => `${u.name} ${u.email}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      <PageHeader eyebrow="Management" title="Users" desc={`${users.length} registered accounts.`} />
      <input placeholder="Search by name or email…" value={q} onChange={(e) => setQ(e.target.value)} className={`${inputCls} mb-4 max-w-sm`} data-testid="user-search" />
      <DataTable head={["Name", "Email", "Sign-in", "Role", "Joined"]} testid="users-table">
        {rows.map((u) => (
          <tr key={u.id} className="border-t border-gray-800" data-testid={`user-row-${u.id}`}>
            <td className="p-3 text-white">{u.name}</td>
            <td className="p-3 text-gray-300">{u.email}</td>
            <td className="p-3">{u.auth_provider === "google" ? <Pill tone="blue">GOOGLE</Pill> : <Pill tone="gray">EMAIL</Pill>}</td>
            <td className="p-3">
              <select value={u.role} disabled={u.id === me?.id} onChange={(e) => changeRole(u, e.target.value)}
                      className={`${inputCls} mt-0 py-1 w-36 disabled:opacity-50`} data-testid={`user-role-${u.id}`}>
                {ROLES.map((r) => <option key={r} value={r}>{r.replace("_", " ")}</option>)}
              </select>
            </td>
            <td className="p-3 text-gray-400 whitespace-nowrap">{new Date(u.created_at).toLocaleDateString()}</td>
          </tr>
        ))}
      </DataTable>
    </div>
  );
}
