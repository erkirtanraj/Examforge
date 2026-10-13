import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { Copy, RefreshCw, PlugZap, Loader2, CreditCard, Webhook } from "lucide-react";
import { api } from "../../lib/api";
import { PageHeader, Field, Pill, inputCls, errMsg } from "../../components/admin/kit";
import { Button } from "../../components/ui/button";

const MODE = { demo: ["gray", "DEMO MODE · NO KEYS"], test: ["amber", "TEST MODE"], live: ["emerald", "LIVE MODE"] };
const copy = (v) => navigator.clipboard.writeText(v).then(() => toast.success("Copied"));

export default function Settings() {
  const [s, setS] = useState(null);
  const [form, setForm] = useState({ razorpay_key_id: "", razorpay_key_secret: "", razorpay_webhook_secret: "" });
  const [busy, setBusy] = useState("");
  const webhookUrl = `${process.env.REACT_APP_BACKEND_URL}/api/webhooks/razorpay`;

  const apply = (d) => {
    setS(d);
    setForm({ razorpay_key_id: d.razorpay_key_id || "", razorpay_key_secret: "", razorpay_webhook_secret: d.razorpay_webhook_secret || "" });
  };
  useEffect(() => { api.get("/admin/settings/payment").then((r) => apply(r.data)); }, []);

  const act = async (name, fn) => {
    setBusy(name);
    try { await fn(); } catch (e) { toast.error(errMsg(e)); } finally { setBusy(""); }
  };
  const save = (e) => { e.preventDefault(); act("save", async () => { apply((await api.put("/admin/settings/payment", form)).data); toast.success("Payment settings saved"); }); };
  const generate = () => act("gen", async () => {
    const { data } = await api.post("/admin/settings/payment/webhook-secret");
    setForm((f) => ({ ...f, razorpay_webhook_secret: data.razorpay_webhook_secret }));
    toast.success("New webhook secret generated and saved. Paste it into Razorpay.");
  });
  const test = () => act("test", async () => { await api.post("/admin/settings/payment/test"); toast.success("Razorpay accepted these keys"); });

  if (!s) return <div className="text-gray-400 text-sm">Loading settings…</div>;
  const [tone, label] = MODE[s.mode];
  return (
    <div className="max-w-3xl">
      <PageHeader eyebrow="System" title="Settings" desc="Payment gateway configuration. Changes apply instantly — no restart needed." />
      <form onSubmit={save} className="space-y-6">
        <section className="card-elev p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 heading-font font-semibold text-white"><CreditCard className="w-5 h-5 text-cyan-300" />Razorpay API keys</div>
            <span data-testid="payment-mode"><Pill tone={tone}>{label}</Pill></span>
          </div>
          <p className="text-sm text-gray-400">Find these in Razorpay Dashboard → Account &amp; Settings → API Keys. Use <span className="mono-font">rzp_test_</span> keys first, then switch to <span className="mono-font">rzp_live_</span>.</p>
          <Field label="Key ID">
            <input value={form.razorpay_key_id} onChange={(e) => setForm({ ...form, razorpay_key_id: e.target.value })} placeholder="rzp_test_xxxxxxxxxxxx" className={`${inputCls} mono-font`} data-testid="rzp-key-id-input" />
          </Field>
          <Field label={s.has_secret ? `Key Secret (saved ${s.secret_hint} — leave blank to keep)` : "Key Secret"}>
            <input type="password" autoComplete="new-password" value={form.razorpay_key_secret} onChange={(e) => setForm({ ...form, razorpay_key_secret: e.target.value })} className={`${inputCls} mono-font`} data-testid="rzp-key-secret-input" />
          </Field>
        </section>

        <section className="card-elev p-6 space-y-4">
          <div className="flex items-center gap-2 heading-font font-semibold text-white"><Webhook className="w-5 h-5 text-cyan-300" />Webhook <span className="text-xs text-gray-500 font-normal">(optional, recommended)</span></div>
          <p className="text-sm text-gray-400">Confirms payments even if a student closes the browser mid-checkout. In Razorpay → Webhooks, add the URL below, select the <span className="mono-font">payment.captured</span> event and paste the secret.</p>
          <Field label="Webhook URL">
            <div className="flex gap-2 mt-1.5">
              <input readOnly value={webhookUrl} className={`${inputCls} mt-0 mono-font text-xs`} data-testid="webhook-url" />
              <button type="button" onClick={() => copy(webhookUrl)} className="px-3 rounded-md border border-gray-800 text-gray-300 hover:bg-gray-800" data-testid="copy-webhook-url"><Copy className="w-4 h-4" /></button>
            </div>
          </Field>
          <Field label="Webhook secret">
            <div className="flex gap-2 mt-1.5">
              <input value={form.razorpay_webhook_secret} onChange={(e) => setForm({ ...form, razorpay_webhook_secret: e.target.value })} placeholder="Generate one or paste your own" className={`${inputCls} mt-0 mono-font text-xs`} data-testid="webhook-secret-input" />
              <button type="button" onClick={() => form.razorpay_webhook_secret && copy(form.razorpay_webhook_secret)} className="px-3 rounded-md border border-gray-800 text-gray-300 hover:bg-gray-800" data-testid="copy-webhook-secret"><Copy className="w-4 h-4" /></button>
              <Button type="button" onClick={generate} disabled={busy === "gen"} variant="outline" className="border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800 whitespace-nowrap" data-testid="generate-webhook-secret">
                {busy === "gen" ? <Loader2 className="w-4 h-4 animate-spin" /> : <><RefreshCw className="w-4 h-4 mr-1" />Generate</>}
              </Button>
            </div>
          </Field>
        </section>

        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy === "save"} className="bg-blue-600 hover:bg-blue-700" data-testid="save-payment-settings">
            {busy === "save" ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save settings"}
          </Button>
          <Button type="button" onClick={test} disabled={busy === "test" || s.mode === "demo"} variant="outline" className="border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800" data-testid="test-payment-settings">
            {busy === "test" ? <Loader2 className="w-4 h-4 animate-spin" /> : <><PlugZap className="w-4 h-4 mr-1" />Test connection</>}
          </Button>
        </div>
      </form>
    </div>
  );
}
