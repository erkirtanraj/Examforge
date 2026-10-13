import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Mail, Send } from "lucide-react";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { PageHeader, Field, Pill, inputCls, errMsg } from "../../components/admin/kit";
import { Button } from "../../components/ui/button";

const PORTS = { starttls: 587, ssl: 465, none: 25 };

export default function EmailSettings() {
  const { user } = useAuth();
  const [f, setF] = useState(null);
  const [saving, setSaving] = useState(false);
  const [testTo, setTestTo] = useState("");
  const [testing, setTesting] = useState(false);
  useEffect(() => {
    api.get("/admin/settings/email").then((r) => setF({ ...r.data, password: "", site_url: r.data.site_url || window.location.origin }));
    setTestTo(user?.email || "");
  }, [user]);
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await api.put("/admin/settings/email", { ...f, port: Number(f.port), password: f.password || null });
      setF({ ...data, password: "" });
      toast.success("Email settings saved");
    } catch (err) { toast.error(errMsg(err)); } finally { setSaving(false); }
  };
  const test = async () => {
    setTesting(true);
    try { await api.post("/admin/settings/email/test", { to: testTo }); toast.success(`Test email sent to ${testTo}`); }
    catch (err) { toast.error(errMsg(err)); } finally { setTesting(false); }
  };

  if (!f) return <div className="text-gray-400 text-sm">Loading…</div>;
  const configured = !!f.updated_at && !!f.host;
  return (
    <div className="max-w-3xl">
      <PageHeader eyebrow="Settings" title="Email (SMTP)" desc="Used to send password reset links. Works with cPanel mail, Gmail (app password), Zoho, Outlook and most providers." />
      <form onSubmit={save} className="space-y-6">
        <section className="card-elev p-6 space-y-4" data-testid="smtp-settings">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 heading-font font-semibold text-white"><Mail className="w-5 h-5 text-cyan-300" />SMTP server</div>
            <span data-testid="smtp-status">{configured ? <Pill tone="emerald">CONFIGURED</Pill> : <Pill tone="amber">NOT SET UP</Pill>}</span>
          </div>
          <div className="grid sm:grid-cols-3 gap-4">
            <Field label="Host" className="sm:col-span-2"><input required value={f.host} onChange={(e) => set("host", e.target.value)} placeholder="mail.yourdomain.com" className={inputCls} data-testid="smtp-host" /></Field>
            <Field label="Port"><input required type="number" value={f.port} onChange={(e) => set("port", e.target.value)} className={inputCls} data-testid="smtp-port" /></Field>
          </div>
          <Field label="Security">
            <select value={f.security} onChange={(e) => setF((p) => ({ ...p, security: e.target.value, port: PORTS[e.target.value] }))} className={inputCls} data-testid="smtp-security">
              <option value="starttls">STARTTLS (port 587)</option><option value="ssl">SSL / TLS (port 465)</option><option value="none">None (not recommended)</option>
            </select>
          </Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Username"><input value={f.username} onChange={(e) => set("username", e.target.value)} placeholder="no-reply@yourdomain.com" className={inputCls} data-testid="smtp-username" autoComplete="off" /></Field>
            <Field label={f.has_password ? "Password (leave blank to keep saved)" : "Password"}>
              <input type="password" value={f.password} onChange={(e) => set("password", e.target.value)} placeholder={f.has_password ? "••••••••  saved" : ""} className={inputCls} data-testid="smtp-password" autoComplete="new-password" />
            </Field>
            <Field label="From email"><input required type="email" value={f.from_email} onChange={(e) => set("from_email", e.target.value)} placeholder="no-reply@yourdomain.com" className={inputCls} data-testid="smtp-from-email" /></Field>
            <Field label="From name"><input value={f.from_name} onChange={(e) => set("from_name", e.target.value)} placeholder="ExamForge" className={inputCls} data-testid="smtp-from-name" /></Field>
          </div>
          <Field label="Website URL (used in reset links)"><input required value={f.site_url} onChange={(e) => set("site_url", e.target.value)} className={`${inputCls} mono-font text-xs`} data-testid="smtp-site-url" /></Field>
        </section>
        <Button type="submit" disabled={saving} className="bg-blue-600 hover:bg-blue-700" data-testid="save-smtp">{saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save email settings"}</Button>
      </form>

      <section className="card-elev p-6 mt-6 space-y-3" data-testid="smtp-test">
        <div className="heading-font font-semibold text-white">Send a test email</div>
        <p className="text-sm text-gray-400">Save your settings first, then send a test to confirm they work.</p>
        <div className="flex flex-col sm:flex-row gap-2">
          <input type="email" value={testTo} onChange={(e) => setTestTo(e.target.value)} className={`${inputCls} mt-0`} data-testid="smtp-test-to" />
          <Button type="button" onClick={test} disabled={testing || !configured || !testTo} variant="outline" className="border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800 shrink-0" data-testid="smtp-test-send">
            {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Send className="w-4 h-4 mr-1" />Send test</>}
          </Button>
        </div>
      </section>
    </div>
  );
}
