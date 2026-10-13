import React, { useMemo } from "react";
import { PageHeader, DataTable, Pill, RowActions, NewButton, FormDialog, Field, inputCls, CategorySelect, rupees, useResource, useEditor, useCategories } from "../../components/admin/kit";

const BLANK = { title: "", description: "", category_id: "", file_url: "", is_free: true, price_rupees: 0 };

export default function Materials() {
  const { items, loading, save, remove } = useResource("/study-materials", "study-materials");
  const cats = useCategories();
  const ed = useEditor(BLANK);
  const catName = useMemo(() => Object.fromEntries(cats.map((c) => [c.id, c.name])), [cats]);
  const f = ed.form;

  const submit = () => ed.run(() => save(ed.editingId, {
    title: f.title, description: f.description, category_id: f.category_id || null, file_url: f.file_url || null,
    is_free: f.is_free, price: f.is_free ? 0 : Math.round(Number(f.price_rupees) * 100),
  }, "/study-materials"));

  return (
    <div>
      <PageHeader eyebrow="Content" title="Study materials" desc="Notes, PYQ papers and downloadable PDFs."
                  action={<NewButton onClick={ed.openNew} label="New material" testid="new-material-btn" />} />
      <DataTable head={["Title", "Category", "File", "Price", ""]} testid="materials-table"
                 empty={!loading && !items.length ? "No study materials yet." : null}>
        {items.map((m) => (
          <tr key={m.id} className="border-t border-gray-800 hover:bg-gray-900/40" data-testid={`material-row-${m.id}`}>
            <td className="p-3 text-white">{m.title}</td>
            <td className="p-3 text-gray-400">{catName[m.category_id] || "—"}</td>
            <td className="p-3 max-w-[200px] truncate">{m.file_url ? <a href={m.file_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">Open</a> : "—"}</td>
            <td className="p-3">{m.is_free ? <Pill tone="emerald">FREE</Pill> : <Pill tone="amber">{rupees(m.price)}</Pill>}</td>
            <td className="p-3"><RowActions id={m.id} onDelete={() => remove(m.id)}
                  onEdit={() => ed.openEdit(m, (x) => ({ ...x, category_id: x.category_id || "", file_url: x.file_url || "", price_rupees: (x.price || 0) / 100 }))} /></td>
          </tr>
        ))}
      </DataTable>

      <FormDialog open={ed.open} onOpenChange={ed.setOpen} title={ed.editingId ? "Edit material" : "New material"} onSubmit={submit} saving={ed.saving} testid="material-form">
        <Field label="Title"><input required value={f.title} onChange={(e) => ed.set("title", e.target.value)} className={inputCls} data-testid="material-title-input" /></Field>
        <Field label="Description"><textarea rows={2} value={f.description} onChange={(e) => ed.set("description", e.target.value)} className={inputCls} data-testid="material-description-input" /></Field>
        <Field label="Category"><CategorySelect value={f.category_id} onChange={(v) => ed.set("category_id", v)} categories={cats} testid="material-category-input" /></Field>
        <Field label="File URL (PDF link)"><input value={f.file_url} onChange={(e) => ed.set("file_url", e.target.value)} className={inputCls} data-testid="material-url-input" /></Field>
        <label className="flex items-center gap-2 text-sm text-gray-300">
          <input type="checkbox" checked={f.is_free} onChange={(e) => ed.set("is_free", e.target.checked)} data-testid="material-free-input" /> Free download
        </label>
        <Field label="Price (₹)"><input type="number" min="0" disabled={f.is_free} value={f.price_rupees} onChange={(e) => ed.set("price_rupees", e.target.value)} className={`${inputCls} disabled:opacity-40`} data-testid="material-price-input" /></Field>
      </FormDialog>
    </div>
  );
}
