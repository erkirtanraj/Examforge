import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Eye, EyeOff, Wand2 } from "lucide-react";
import { api } from "../../lib/api";
import { FormDialog, Field, inputCls, errMsg } from "./kit";

export const ROLES = ["student", "teacher", "support", "admin", "super_admin"];
const genPw = () => Array.from(crypto.getRandomValues(new Uint8Array(10)), (b) => "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"[b % 56]).join("");

const PasswordInput = ({ value, onChange, testid }) => {
  const [show, setShow] = useState(false);
  return (
    <div className="mt-1.5 flex gap-2">
      <div className="relative flex-1">
        <input type={show ? "text" : "password"} value={value} onChange={(e) => onChange(e.target.value)} minLength={6} required
               className={`${inputCls} mt-0 pr-9 mono-font`} data-testid={testid} autoComplete="new-password" />
        <button type="button" onClick={() => setShow(!show)} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white" aria-label="Show password" data-testid={`${testid}-toggle`}>
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
      <button type="button" onClick={() => { onChange(genPw()); setShow(true); }} className="px-3 rounded-md border border-gray-700 text-xs text-gray-300 hover:bg-gray-800 inline-flex items-center gap-1 normal-case tracking-normal" data-testid={`${testid}-generate`}>
        <Wand2 className="w-3.5 h-3.5" /> Generate
      </button>
    </div>
  );
};

export function UserFormDialog({ open, onOpenChange, user, me, onSaved }) {
  const isNew = !user;
  const [f, setF] = useState({});
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    if (open) setF(user ? { name: user.name, email: user.email, phone: user.phone || "", role: user.role } : { name: "", email: "", phone: "", role: "student", password: "" });
  }, [open, user]);
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const roles = me?.role === "super_admin" ? ROLES : ROLES.filter((r) => r !== "super_admin");
  const submit = async () => {
    setSaving(true);
    try {
      if (isNew) await api.post("/admin/users", f); else await api.put(`/admin/users/${user.id}`, f);
      toast.success(isNew ? "User created" : "Profile updated");
      onOpenChange(false);
      onSaved();
    } catch (e) { toast.error(errMsg(e)); } finally { setSaving(false); }
  };
  return (
    <FormDialog open={open} onOpenChange={onOpenChange} title={isNew ? "New user" : "Edit user"} onSubmit={submit} saving={saving} testid="user-form-dialog">
      <Field label="Full name"><input required value={f.name || ""} onChange={(e) => set("name", e.target.value)} className={inputCls} data-testid="user-name-input" /></Field>
      <div className="grid sm:grid-cols-2 gap-3">
        <Field label="Email"><input required type="email" value={f.email || ""} onChange={(e) => set("email", e.target.value)} className={inputCls} data-testid="user-email-input" /></Field>
        <Field label="Phone"><input value={f.phone || ""} onChange={(e) => set("phone", e.target.value)} className={inputCls} data-testid="user-phone-input" /></Field>
      </div>
      <Field label="Role">
        <select value={f.role || "student"} disabled={user?.id === me?.id || (user?.role === "super_admin" && me?.role !== "super_admin")} onChange={(e) => set("role", e.target.value)} className={`${inputCls} disabled:opacity-50`} data-testid="user-role-input">
          {(f.role === "super_admin" && !roles.includes("super_admin") ? ROLES : roles).map((r) => <option key={r} value={r}>{r.replace("_", " ")}</option>)}
        </select>
      </Field>
      {isNew && <Field label="Password (min 6 characters)"><PasswordInput value={f.password || ""} onChange={(v) => set("password", v)} testid="user-password-input" /></Field>}
      {!isNew && <p className="text-xs text-gray-500">Changing the email or role signs this user out of all devices.</p>}
    </FormDialog>
  );
}

export function ResetPasswordDialog({ user, onOpenChange }) {
  const [pw, setPw] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (user) setPw(""); }, [user]);
  const submit = async () => {
    if (pw.length < 6) return toast.error("Password must be at least 6 characters");
    setSaving(true);
    try {
      await api.post(`/admin/users/${user.id}/reset-password`, { password: pw });
      toast.success(`Password reset for ${user.name}. Share it with them securely.`);
      onOpenChange(false);
    } catch (e) { toast.error(errMsg(e)); } finally { setSaving(false); }
  };
  return (
    <FormDialog open={!!user} onOpenChange={onOpenChange} title={`Reset password · ${user?.name || ""}`} onSubmit={submit} saving={saving} testid="reset-password-dialog">
      <p className="text-sm text-gray-400">Set a new password for <span className="text-white">{user?.email}</span>. They'll be signed out everywhere and must use the new password.</p>
      <Field label="New password"><PasswordInput value={pw} onChange={setPw} testid="reset-password-input" /></Field>
    </FormDialog>
  );
}
