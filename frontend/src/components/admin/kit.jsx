import React, { useCallback, useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../ui/dialog";
import { Button } from "../ui/button";
import { Loader2, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "../../lib/api";

export const inputCls =
  "w-full mt-1.5 px-3 py-2 rounded-md bg-[#0b1120] border border-gray-800 text-white text-sm normal-case tracking-normal font-sans focus:outline-none focus:border-blue-500 transition-colors";

export const rupees = (p) => `₹${((p || 0) / 100).toFixed(0)}`;

export const errMsg = (e, fallback = "Something went wrong") => {
  const d = e?.response?.data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg).join(", ");
  return fallback;
};

export const PageHeader = ({ eyebrow, title, desc, action }) => (
  <div className="flex flex-wrap items-end justify-between gap-4 mb-6 fade-in">
    <div>
      <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mb-1">{eyebrow}</div>
      <h1 className="heading-font text-2xl sm:text-3xl font-bold text-white">{title}</h1>
      {desc && <p className="text-sm text-gray-400 mt-1">{desc}</p>}
    </div>
    {action}
  </div>
);

export const Field = ({ label, children, className = "" }) => (
  <label className={`block text-[11px] text-gray-400 mono-font uppercase tracking-wider ${className}`}>
    {label}
    {children}
  </label>
);

export const DataTable = ({ head, children, empty, testid }) => (
  <div className="card-elev overflow-x-auto" data-testid={testid}>
    <table className="w-full text-sm">
      <thead className="bg-gray-900/60">
        <tr className="text-left text-gray-400 mono-font text-xs uppercase">
          {head.map((h) => <th key={h} className="p-3 font-medium whitespace-nowrap">{h}</th>)}
        </tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
    {empty && <div className="p-8 text-center text-gray-500 text-sm">{empty}</div>}
  </div>
);

const TONES = {
  blue: "border-blue-500/30 bg-blue-500/10 text-blue-300",
  emerald: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  amber: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  rose: "border-rose-500/40 bg-rose-500/10 text-rose-300",
  gray: "border-gray-700 bg-gray-800/40 text-gray-300",
};
export const Pill = ({ tone = "blue", children }) => (
  <span className={`text-xs mono-font px-2 py-0.5 rounded border whitespace-nowrap ${TONES[tone]}`}>{children}</span>
);

export const NewButton = ({ onClick, label, testid }) => (
  <Button onClick={onClick} data-testid={testid} className="bg-blue-600 hover:bg-blue-700">+ {label}</Button>
);

export const RowActions = ({ onEdit, onDelete, id }) => (
  <div className="flex justify-end gap-1">
    {onEdit && (
      <button onClick={onEdit} data-testid={`edit-${id}`} title="Edit"
              className="p-2 rounded-md text-gray-400 hover:text-white hover:bg-gray-800 transition-colors">
        <Pencil className="w-4 h-4" />
      </button>
    )}
    {onDelete && (
      <button onClick={onDelete} data-testid={`delete-${id}`} title="Delete"
              className="p-2 rounded-md text-gray-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors">
        <Trash2 className="w-4 h-4" />
      </button>
    )}
  </div>
);

export const FormDialog = ({ open, onOpenChange, title, onSubmit, saving, children, testid, wide }) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent data-testid={testid}
      className={`bg-[#0b1120] border-gray-800 text-white max-h-[90vh] overflow-y-auto ${wide ? "sm:max-w-3xl" : "sm:max-w-lg"}`}>
      <DialogHeader><DialogTitle className="heading-font">{title}</DialogTitle></DialogHeader>
      <form onSubmit={(e) => { e.preventDefault(); onSubmit(); }} className="space-y-4">
        {children}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}
                  className="border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800">Cancel</Button>
          <Button type="submit" disabled={saving} data-testid={`${testid}-save`} className="bg-blue-600 hover:bg-blue-700">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save"}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
);

// List + create/update/delete for one content kind
export function useResource(listUrl, kind) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(
    () => api.get(listUrl).then((r) => setItems(r.data)).finally(() => setLoading(false)),
    [listUrl]
  );
  useEffect(() => { reload(); }, [reload]);
  const save = async (id, payload, createUrl) => {
    if (id) await api.put(`/content/${kind}/${id}`, payload);
    else await api.post(createUrl, payload);
    toast.success(id ? "Changes saved" : "Created");
    await reload();
  };
  const remove = async (id) => {
    if (!window.confirm("Delete this item? This cannot be undone.")) return;
    try {
      await api.delete(`/content/${kind}/${id}`);
      toast.success("Deleted");
      await reload();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return { items, loading, reload, save, remove };
}

// Shared hook for a dialog form editing one record
export function useEditor(blank) {
  const [open, setOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(blank);
  const [saving, setSaving] = useState(false);
  const openNew = () => { setEditingId(null); setForm(blank); setOpen(true); };
  const openEdit = (item, map = (x) => x) => { setEditingId(item.id); setForm({ ...blank, ...map(item) }); setOpen(true); };
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const run = async (fn) => {
    setSaving(true);
    try { await fn(); setOpen(false); } catch (e) { toast.error(errMsg(e)); } finally { setSaving(false); }
  };
  return { open, setOpen, editingId, form, setForm, set, saving, openNew, openEdit, run };
}

export const CategorySelect = ({ value, onChange, categories, testid, allowAll }) => (
  <select value={value || ""} onChange={(e) => onChange(e.target.value)} className={inputCls} data-testid={testid}>
    <option value="">{allowAll ? "All categories" : "— None —"}</option>
    {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
  </select>
);

export function useCategories() {
  const [cats, setCats] = useState([]);
  useEffect(() => { api.get("/categories").then((r) => setCats(r.data)); }, []);
  return cats;
}
