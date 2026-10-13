import React, { useMemo } from "react";
import { PageHeader, DataTable, Pill, RowActions, NewButton, FormDialog, Field, inputCls, CategorySelect, rupees, useResource, useEditor, useCategories } from "../../components/admin/kit";

const BLANK = { title: "", description: "", category_id: "", thumbnail: "", language: "en", is_free: true, price_rupees: 0, validity_days: 365 };

export default function Series() {
  const { items, loading, save, remove } = useResource("/test-series", "test-series");
  const cats = useCategories();
  const ed = useEditor(BLANK);
  const catName = useMemo(() => Object.fromEntries(cats.map((c) => [c.id, c.name])), [cats]);
  const f = ed.form;

  const submit = () => ed.run(() => save(ed.editingId, {
    title: f.title, description: f.description, category_id: f.category_id || null, thumbnail: f.thumbnail || null,
    language: f.language, is_free: f.is_free, price: f.is_free ? 0 : Math.round(Number(f.price_rupees) * 100),
    validity_days: Number(f.validity_days),
  }, "/test-series"));

  return (
    <div>
      <PageHeader eyebrow="Content" title="Test series" desc="Bundles of tests that students enroll in or buy."
                  action={<NewButton onClick={ed.openNew} label="New series" testid="new-series-btn" />} />
      <DataTable head={["Title", "Category", "Tests", "Price", "Validity", ""]} testid="series-table"
                 empty={!loading && !items.length ? "No test series yet." : null}>
        {items.map((s) => (
          <tr key={s.id} className="border-t border-gray-800 hover:bg-gray-900/40" data-testid={`series-row-${s.id}`}>
            <td className="p-3 text-white">{s.title}</td>
            <td className="p-3 text-gray-400">{catName[s.category_id] || "—"}</td>
            <td className="p-3 mono-font text-gray-300">{s.tests_count}</td>
            <td className="p-3">{s.is_free ? <Pill tone="emerald">FREE</Pill> : <Pill tone="amber">{rupees(s.price)}</Pill>}</td>
            <td className="p-3 text-gray-400 whitespace-nowrap">{s.validity_days} days</td>
            <td className="p-3"><RowActions id={s.id} onDelete={() => remove(s.id)}
                  onEdit={() => ed.openEdit(s, (x) => ({ ...x, category_id: x.category_id || "", thumbnail: x.thumbnail || "", price_rupees: (x.price || 0) / 100 }))} /></td>
          </tr>
        ))}
      </DataTable>

      <FormDialog open={ed.open} onOpenChange={ed.setOpen} title={ed.editingId ? "Edit test series" : "New test series"}
                  onSubmit={submit} saving={ed.saving} testid="series-form">
        <Field label="Title"><input required value={f.title} onChange={(e) => ed.set("title", e.target.value)} className={inputCls} data-testid="series-title-input" /></Field>
        <Field label="Description"><textarea rows={3} value={f.description} onChange={(e) => ed.set("description", e.target.value)} className={inputCls} data-testid="series-description-input" /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Category"><CategorySelect value={f.category_id} onChange={(v) => ed.set("category_id", v)} categories={cats} testid="series-category-input" /></Field>
          <Field label="Language">
            <select value={f.language} onChange={(e) => ed.set("language", e.target.value)} className={inputCls} data-testid="series-language-input">
              <option value="en">English</option><option value="hi">Hindi</option><option value="bilingual">Bilingual</option>
            </select>
          </Field>
        </div>
        <Field label="Thumbnail URL"><input value={f.thumbnail} onChange={(e) => ed.set("thumbnail", e.target.value)} className={inputCls} data-testid="series-thumbnail-input" /></Field>
        <label className="flex items-center gap-2 text-sm text-gray-300">
          <input type="checkbox" checked={f.is_free} onChange={(e) => ed.set("is_free", e.target.checked)} data-testid="series-free-input" /> Free series
        </label>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Price (₹)"><input type="number" min="0" disabled={f.is_free} value={f.price_rupees} onChange={(e) => ed.set("price_rupees", e.target.value)} className={`${inputCls} disabled:opacity-40`} data-testid="series-price-input" /></Field>
          <Field label="Validity (days)"><input type="number" min="1" value={f.validity_days} onChange={(e) => ed.set("validity_days", e.target.value)} className={inputCls} data-testid="series-validity-input" /></Field>
        </div>
      </FormDialog>
    </div>
  );
}
