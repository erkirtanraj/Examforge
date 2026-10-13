import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Loader2, Megaphone } from "lucide-react";
import { api } from "../../lib/api";
import { useSite } from "../../lib/site";
import { PageHeader, Field, Pill, inputCls, errMsg } from "../../components/admin/kit";
import { AnnouncementView } from "../../components/AnnouncementBar";
import { Switch } from "../../components/ui/switch";
import { Button } from "../../components/ui/button";

const STYLES = [["offer", "Offer"], ["info", "Info"], ["live", "Live"], ["warning", "Warning"]];
const toLocal = (iso) => { if (!iso) return ""; const d = new Date(iso); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16); };
const toIso = (v) => (v ? new Date(v).toISOString() : null);

const status = (f) => {
  if (!f.enabled) return ["gray", "OFF"];
  const now = new Date();
  if (f.starts_at && new Date(f.starts_at) > now) return ["amber", "SCHEDULED"];
  if (f.ends_at && new Date(f.ends_at) <= now) return ["rose", "EXPIRED"];
  return ["emerald", "LIVE ON HOME PAGE"];
};

export default function AnnouncementSettings() {
  const { reload } = useSite();
  const [f, setF] = useState(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => { api.get("/admin/site").then((r) => setF(r.data.announcement)); }, []);
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await api.put("/admin/site/announcement", f);
      setF(data.announcement);
      await reload();
      toast.success("Announcement saved");
    } catch (err) { toast.error(errMsg(err)); }
    finally { setSaving(false); }
  };

  if (!f) return <div className="text-gray-400 text-sm">Loading…</div>;
  const [tone, label] = status(f);
  return (
    <div className="max-w-3xl">
      <PageHeader eyebrow="Settings" title="Announcement Bar" desc="A banner at the top of the home page for new mocks, offers or notices. Visitors can close it; it reappears when you save a change." />
      <form onSubmit={save} className="space-y-6">
        <section className="card-elev p-6 space-y-5" data-testid="announcement-settings">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 heading-font font-semibold text-white"><Megaphone className="w-5 h-5 text-cyan-300" />Banner</div>
            <div className="flex items-center gap-3">
              <span data-testid="announcement-status"><Pill tone={tone}>{label}</Pill></span>
              <Switch checked={f.enabled} onCheckedChange={(v) => set("enabled", v)} data-testid="announcement-enabled-switch" />
            </div>
          </div>
          <Field label="Message">
            <input value={f.message} maxLength={180} onChange={(e) => set("message", e.target.value)} placeholder="All-India Live Mock this Sunday at 10 AM" className={inputCls} data-testid="announcement-message-input" />
          </Field>
          <Field label="Colour style">
            <div className="mt-1.5 flex flex-wrap gap-2">
              {STYLES.map(([k, l]) => (
                <button key={k} type="button" onClick={() => set("style", k)} data-testid={`announcement-style-${k}`}
                        className={`px-3 py-1.5 rounded-md border text-xs normal-case tracking-normal transition-colors ${f.style === k ? "border-cyan-400 bg-cyan-500/10 text-white" : "border-gray-800 text-gray-400 hover:text-white"}`}>{l}</button>
              ))}
            </div>
          </Field>
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Button text (optional)"><input value={f.cta_label} onChange={(e) => set("cta_label", e.target.value)} placeholder="Register now" className={inputCls} data-testid="announcement-cta-label" /></Field>
            <Field label="Button link"><input value={f.cta_url} onChange={(e) => set("cta_url", e.target.value)} placeholder="/test-series" className={inputCls} data-testid="announcement-cta-url" /></Field>
            <Field label="Coupon code (optional)"><input value={f.coupon_code} onChange={(e) => set("coupon_code", e.target.value.toUpperCase())} placeholder="WELCOME20" className={`${inputCls} mono-font`} data-testid="announcement-coupon-input" /></Field>
            <div />
            <Field label="Start (optional)"><input type="datetime-local" value={toLocal(f.starts_at)} onChange={(e) => set("starts_at", toIso(e.target.value))} className={inputCls} data-testid="announcement-starts-at" /></Field>
            <Field label="End (optional)"><input type="datetime-local" value={toLocal(f.ends_at)} onChange={(e) => set("ends_at", toIso(e.target.value))} className={inputCls} data-testid="announcement-ends-at" /></Field>
          </div>
        </section>

        <section className="space-y-2">
          <div className="text-[11px] text-gray-400 mono-font uppercase tracking-wider">Preview</div>
          <div className="rounded-md overflow-hidden border border-gray-800" data-testid="announcement-preview">
            {f.message ? <AnnouncementView a={f} /> : <div className="p-4 text-sm text-gray-500">Type a message to see the preview.</div>}
          </div>
        </section>

        <Button type="submit" disabled={saving} className="bg-blue-600 hover:bg-blue-700" data-testid="save-announcement">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save announcement"}
        </Button>
      </form>
    </div>
  );
}
