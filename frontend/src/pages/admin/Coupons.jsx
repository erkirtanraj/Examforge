import React, { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { PageHeader, DataTable, Pill, RowActions, NewButton, FormDialog, Field, inputCls, rupees, useEditor, errMsg } from "../../components/admin/kit";
import { toast } from "sonner";

const BLANK = { code: "", discount_type: "percent", value: 10, max_uses: "", valid_until: "", item_ids: [], active: true, description: "" };
const toLocal = (iso) => { const d = new Date(iso); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16); };

export default function Coupons() {
  const [items, setItems] = useState([]);
  const [series, setSeries] = useState([]);
  const ed = useEditor(BLANK);
  const f = ed.form;
  const load = () => api.get("/admin/coupons").then((r) => setItems(r.data));
  useEffect(() => { load(); api.get("/test-series").then((r) => setSeries(r.data.filter((s) => !s.is_free))); }, []);
  const title = Object.fromEntries(series.map((s) => [s.id, s.title]));

  const submit = () => ed.run(async () => {
    const payload = { ...f, value: Number(f.value), max_uses: f.max_uses === "" ? null : Number(f.max_uses),
                      valid_until: f.valid_until ? new Date(f.valid_until).toISOString() : null };
    if (ed.editingId) await api.put(`/admin/coupons/${ed.editingId}`, payload);
    else await api.post("/admin/coupons", payload);
    toast.success("Coupon saved");
    await load();
  });
  const remove = async (c) => {
    if (!window.confirm(`Delete coupon ${c.code}?`)) return;
    try { await api.delete(`/admin/coupons/${c.id}`); toast.success("Deleted"); load(); } catch (e) { toast.error(errMsg(e)); }
  };
  const toggleItem = (id) => ed.set("item_ids", f.item_ids.includes(id) ? f.item_ids.filter((x) => x !== id) : [...f.item_ids, id]);
  const expired = (c) => c.valid_until && new Date(c.valid_until) < new Date();

  return (
    <div>
      <PageHeader eyebrow="Management" title="Coupons" desc="Discount codes students enter at checkout. Each student can use a code once."
                  action={<NewButton onClick={ed.openNew} label="New coupon" testid="new-coupon-btn" />} />
      <DataTable head={["Code", "Discount", "Used", "Valid until", "Applies to", "Status", ""]} testid="coupons-table" empty={!items.length ? "No coupons yet." : null}>
        {items.map((c) => (
          <tr key={c.id} className="border-t border-gray-800" data-testid={`coupon-row-${c.code}`}>
            <td className="p-3 mono-font font-semibold text-white">{c.code}<div className="text-xs font-normal text-gray-500 font-sans">{c.description}</div></td>
            <td className="p-3 text-cyan-300 mono-font">{c.discount_type === "percent" ? `${c.value}%` : rupees(c.value * 100)}</td>
            <td className="p-3 mono-font text-gray-300">{c.used_count}{c.max_uses ? ` / ${c.max_uses}` : ""}</td>
            <td className="p-3 text-gray-400 whitespace-nowrap">{c.valid_until ? new Date(c.valid_until).toLocaleString() : "No expiry"}</td>
            <td className="p-3 text-gray-400 max-w-[220px] truncate">{c.item_ids?.length ? c.item_ids.map((id) => title[id] || "—").join(", ") : "All paid items"}</td>
            <td className="p-3">{!c.active ? <Pill tone="gray">PAUSED</Pill> : expired(c) ? <Pill tone="rose">EXPIRED</Pill> : c.max_uses && c.used_count >= c.max_uses ? <Pill tone="amber">USED UP</Pill> : <Pill tone="emerald">ACTIVE</Pill>}</td>
            <td className="p-3"><RowActions id={c.id} onDelete={() => remove(c)}
                  onEdit={() => ed.openEdit(c, (x) => ({ ...x, max_uses: x.max_uses ?? "", valid_until: x.valid_until ? toLocal(x.valid_until) : "", item_ids: x.item_ids || [] }))} /></td>
          </tr>
        ))}
      </DataTable>

      <FormDialog open={ed.open} onOpenChange={ed.setOpen} title={ed.editingId ? "Edit coupon" : "New coupon"} onSubmit={submit} saving={ed.saving} testid="coupon-form">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Code"><input required value={f.code} onChange={(e) => ed.set("code", e.target.value.toUpperCase().replace(/\s/g, ""))} className={`${inputCls} mono-font`} placeholder="DIWALI30" data-testid="coupon-code-input" /></Field>
          <Field label="Description"><input value={f.description} onChange={(e) => ed.set("description", e.target.value)} className={inputCls} data-testid="coupon-description-input" /></Field>
          <Field label="Type">
            <select value={f.discount_type} onChange={(e) => ed.set("discount_type", e.target.value)} className={inputCls} data-testid="coupon-type-input">
              <option value="percent">Percent off</option><option value="flat">Flat ₹ off</option>
            </select>
          </Field>
          <Field label={f.discount_type === "percent" ? "Percent (1–100)" : "Amount (₹)"}><input type="number" min="1" step="any" required value={f.value} onChange={(e) => ed.set("value", e.target.value)} className={inputCls} data-testid="coupon-value-input" /></Field>
          <Field label="Max total uses (blank = unlimited)"><input type="number" min="1" value={f.max_uses} onChange={(e) => ed.set("max_uses", e.target.value)} className={inputCls} data-testid="coupon-max-uses-input" /></Field>
          <Field label="Valid until (optional)"><input type="datetime-local" value={f.valid_until} onChange={(e) => ed.set("valid_until", e.target.value)} className={inputCls} data-testid="coupon-valid-until-input" /></Field>
        </div>
        <div>
          <div className="text-[11px] text-gray-400 mono-font uppercase tracking-wider mb-1.5">Applies to (none selected = all paid items)</div>
          <div className="rounded-md border border-gray-800 max-h-40 overflow-y-auto divide-y divide-gray-800/70">
            {series.map((s) => (
              <label key={s.id} className="flex items-center gap-3 px-3 py-2 text-sm text-gray-200 cursor-pointer hover:bg-gray-900/50">
                <input type="checkbox" checked={f.item_ids.includes(s.id)} onChange={() => toggleItem(s.id)} data-testid={`coupon-item-${s.id}`} />
                <span className="flex-1">{s.title}</span><span className="mono-font text-xs text-gray-500">{rupees(s.price)}</span>
              </label>
            ))}
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-300"><input type="checkbox" checked={f.active} onChange={(e) => ed.set("active", e.target.checked)} data-testid="coupon-active-input" /> Active</label>
      </FormDialog>
    </div>
  );
}
