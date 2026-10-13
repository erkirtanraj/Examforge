import React from "react";
import { PageHeader, DataTable, RowActions, NewButton, FormDialog, Field, inputCls, useResource, useEditor } from "../../components/admin/kit";

const BLANK = { name: "", description: "", icon: "GraduationCap" };
const ICONS = ["GraduationCap", "FileText", "Scale", "Landmark", "Train", "Atom"];
const slugify = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");

export default function Categories() {
  const { items, loading, save, remove } = useResource("/categories", "categories");
  const ed = useEditor(BLANK);
  const f = ed.form;
  const submit = () => ed.run(() => save(ed.editingId, { ...f, slug: f.slug || slugify(f.name) }, "/categories"));

  return (
    <div>
      <PageHeader eyebrow="Content" title="Exam categories" desc="Shown on the home page and used to filter tests, courses and questions."
                  action={<NewButton onClick={ed.openNew} label="New category" testid="new-category-btn" />} />
      <DataTable head={["Name", "Slug", "Description", ""]} testid="categories-table" empty={!loading && !items.length ? "No categories yet." : null}>
        {items.map((c) => (
          <tr key={c.id} className="border-t border-gray-800 hover:bg-gray-900/40" data-testid={`category-row-${c.id}`}>
            <td className="p-3 text-white">{c.name}</td>
            <td className="p-3 mono-font text-xs text-gray-400">{c.slug}</td>
            <td className="p-3 text-gray-400 max-w-sm truncate">{c.description}</td>
            <td className="p-3"><RowActions id={c.id} onEdit={() => ed.openEdit(c)} onDelete={() => remove(c.id)} /></td>
          </tr>
        ))}
      </DataTable>
      <FormDialog open={ed.open} onOpenChange={ed.setOpen} title={ed.editingId ? "Edit category" : "New category"} onSubmit={submit} saving={ed.saving} testid="category-form">
        <Field label="Name"><input required value={f.name} onChange={(e) => ed.set("name", e.target.value)} className={inputCls} data-testid="category-name-input" /></Field>
        <Field label="Description"><input value={f.description} onChange={(e) => ed.set("description", e.target.value)} className={inputCls} data-testid="category-description-input" /></Field>
        <Field label="Icon">
          <select value={f.icon} onChange={(e) => ed.set("icon", e.target.value)} className={inputCls} data-testid="category-icon-input">
            {ICONS.map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
        </Field>
      </FormDialog>
    </div>
  );
}
