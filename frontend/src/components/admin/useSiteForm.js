import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "../../lib/api";
import { useSite } from "../../lib/site";
import { errMsg } from "./kit";

// Loads admin site content and saves a subset of keys to the given endpoint.
export default function useSiteForm(endpoint, keys) {
  const { reload } = useSite();
  const [form, setForm] = useState(null);
  const [metrics, setMetrics] = useState({});
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    api.get("/admin/site").then((r) => { setMetrics(r.data.metrics); setForm(Object.fromEntries(keys.map((k) => [k, r.data[k]]))); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const set = (section, patch) => setForm((f) => ({ ...f, [section]: Array.isArray(patch) ? patch : { ...f[section], ...patch } }));
  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try { await api.put(endpoint, form); await reload(); toast.success("Saved — live on the site now"); }
    catch (err) { toast.error(errMsg(err)); }
    finally { setSaving(false); }
  };
  return { form, set, save, saving, metrics };
}
