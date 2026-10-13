import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Pencil, KeyRound, Ban, CheckCircle2, Trash2, Loader2 } from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { PageHeader, DataTable, Pill, NewButton, inputCls, errMsg } from "../../components/admin/kit";
import { UserFormDialog, ResetPasswordDialog, ROLES } from "../../components/admin/UserDialogs";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "../../components/ui/alert-dialog";

const ROLE_TONE = { super_admin: "rose", admin: "amber", teacher: "blue", support: "gray", student: "emerald" };
const Act = ({ onClick, title, icon: Icon, testid, danger, disabled }) => (
  <button type="button" onClick={onClick} title={title} aria-label={title} disabled={disabled} data-testid={testid}
          className={`p-1.5 rounded text-gray-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed ${danger ? "hover:text-rose-300 hover:bg-rose-500/10" : "hover:text-white hover:bg-gray-800"}`}>
    <Icon className="w-4 h-4" />
  </button>
);

export default function Users() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [form, setForm] = useState({ open: false, user: null });
  const [resetUser, setResetUser] = useState(null);
  const [delUser, setDelUser] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = () => api.get("/admin/users").then((r) => setUsers(r.data));
  useEffect(() => { load(); }, []);

  const locked = (u) => u.role === "super_admin" && me?.role !== "super_admin";
  const toggleStatus = async (u) => {
    const suspend = u.status !== "suspended";
    try {
      await api.put(`/admin/users/${u.id}/status`, { suspended: suspend });
      toast.success(`${u.name} ${suspend ? "suspended" : "re-activated"}`);
      load();
    } catch (e) { toast.error(errMsg(e)); }
  };
  const doDelete = async () => {
    setBusy(true);
    try {
      await api.delete(`/admin/users/${delUser.id}`);
      toast.success(`${delUser.name} deleted`);
      setDelUser(null);
      load();
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };

  const rows = users.filter((u) => (!role || u.role === role) && `${u.name} ${u.email} ${u.phone || ""}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      <PageHeader eyebrow="Management" title="Users" desc={`${users.length} registered accounts.`}
                  action={<NewButton onClick={() => setForm({ open: true, user: null })} label="New user" testid="new-user-btn" />} />
      <div className="flex flex-wrap gap-3 mb-4">
        <input placeholder="Search name, email or phone…" value={q} onChange={(e) => setQ(e.target.value)} className={`${inputCls} mt-0 max-w-sm`} data-testid="user-search" />
        <select value={role} onChange={(e) => setRole(e.target.value)} className={`${inputCls} mt-0 w-44`} data-testid="user-filter-role">
          <option value="">All roles</option>{ROLES.map((r) => <option key={r} value={r}>{r.replace("_", " ")}</option>)}
        </select>
      </div>
      <DataTable head={["Name", "Email", "Phone", "Role", "Status", "Joined", ""]} testid="users-table" empty={!rows.length && "No users match."}>
        {rows.map((u) => {
          const self = u.id === me?.id;
          const suspended = u.status === "suspended";
          return (
            <tr key={u.id} className={`border-t border-gray-800 ${suspended ? "opacity-60" : ""}`} data-testid={`user-row-${u.id}`}>
              <td className="p-3 text-white whitespace-nowrap">{u.name}{self && <span className="ml-2 text-[10px] text-cyan-300 mono-font">YOU</span>}</td>
              <td className="p-3 text-gray-300">{u.email}{u.auth_provider === "google" && <span className="ml-2"><Pill tone="blue">GOOGLE</Pill></span>}</td>
              <td className="p-3 text-gray-400 mono-font text-xs whitespace-nowrap">{u.phone || "—"}</td>
              <td className="p-3"><Pill tone={ROLE_TONE[u.role]}>{u.role.replace("_", " ").toUpperCase()}</Pill></td>
              <td className="p-3" data-testid={`user-status-${u.id}`}>{suspended ? <Pill tone="rose">SUSPENDED</Pill> : <Pill tone="emerald">ACTIVE</Pill>}</td>
              <td className="p-3 text-gray-400 whitespace-nowrap">{new Date(u.created_at).toLocaleDateString()}</td>
              <td className="p-3">
                <div className="flex justify-end gap-0.5">
                  <Act icon={Pencil} title="Edit profile" onClick={() => setForm({ open: true, user: u })} disabled={locked(u)} testid={`user-edit-${u.id}`} />
                  <Act icon={KeyRound} title="Reset password" onClick={() => setResetUser(u)} disabled={locked(u)} testid={`user-reset-${u.id}`} />
                  <Act icon={suspended ? CheckCircle2 : Ban} title={suspended ? "Activate" : "Suspend"} onClick={() => toggleStatus(u)} disabled={self || locked(u)} testid={`user-status-toggle-${u.id}`} danger={!suspended} />
                  <Act icon={Trash2} title="Delete user" onClick={() => setDelUser(u)} disabled={self || locked(u)} testid={`user-delete-${u.id}`} danger />
                </div>
              </td>
            </tr>
          );
        })}
      </DataTable>

      <UserFormDialog open={form.open} onOpenChange={(o) => setForm((f) => ({ ...f, open: o }))} user={form.user} me={me} onSaved={load} />
      <ResetPasswordDialog user={resetUser} onOpenChange={(o) => !o && setResetUser(null)} />
      <AlertDialog open={!!delUser} onOpenChange={(o) => !o && setDelUser(null)}>
        <AlertDialogContent className="bg-[#111827] border-gray-800 text-white" data-testid="user-delete-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {delUser?.name}?</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-400">This permanently removes the account along with their test attempts, results, orders, purchases and course progress. This cannot be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-transparent border-gray-700 text-gray-200 hover:bg-gray-800" data-testid="user-delete-cancel">Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={(e) => { e.preventDefault(); doDelete(); }} disabled={busy} className="bg-rose-600 hover:bg-rose-700" data-testid="user-delete-confirm">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : "Delete user"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
