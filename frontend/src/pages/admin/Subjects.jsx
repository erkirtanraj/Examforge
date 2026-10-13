import React, { useMemo, useState } from "react";
import { toast } from "sonner";
import { api } from "../../lib/api";
import { PageHeader, DataTable, RowActions, NewButton, FormDialog, Field, inputCls, CategorySelect, useCategories, useSubjects, useEditor, errMsg } from "../../components/admin/kit";

const BLANK = { name: "", category_id: "" };

export default function Subjects() {
  const cats = useCategories();
  const [subs, reload] = useSubjects();
  const [cat, setCat] = useState("");
  const ed = useEditor(BLANK);
  const catName = useMemo(() => Object.fromEntries(cats.map((c) => [c.id, c.name])), [cats]);
  const rows = subs.filter((s) => !cat || s.category_id === cat).sort((a, b) => (catName[a.category_id] || "").localeCompare(catName[b.category_id] || "") || a.name.localeCompare(b.name));

  const submit = () => {
    if (!ed.form.name.trim()) return toast.error("Enter a subject name");
    if (!ed.form.category_id) return toast.error("Choose a category");
    ed.run(async () => {
      const body = { name: ed.form.name.trim(), category_id: ed.form.category_id };
      if (ed.editingId) await api.put(`/content/subjects/${ed.editingId}`, body); else await api.post("/subjects", body);
      toast.success("Subject saved");
      await reload();
    });
  };
  const remove = async (s) => {
    if (!window.confirm(`Delete subject "${s.name}"? Questions keep their content but lose this subject tag.`)) return;
    try { await api.delete(`/content/subjects/${s.id}`); toast.success("Deleted"); reload(); } catch (e) { toast.error(errMsg(e)); }
  };

  return (
    <div>
      <PageHeader eyebrow="Content" title="Subjects" desc="Subjects group questions inside a category (e.g. SSC → Quantitative Aptitude) and power the subject-wise report."
                  action={<NewButton onClick={() => { ed.openNew(); if (cat) ed.set("category_id", cat); }} label="New subject" testid="new-subject-btn" />} />
      <div className="max-w-xs mb-4"><CategorySelect value={cat} onChange={setCat} categories={cats} allowAll testid="subject-filter-category" /></div>
      <DataTable head={["Subject", "Category", ""]} testid="subjects-table" empty={!rows.length && "No subjects yet."}>
        {rows.map((s) => (
          <tr key={s.id} className="border-t border-gray-800" data-testid={`subject-row-${s.id}`}>
            <td className="p-3 text-white">{s.name}</td>
            <td className="p-3 text-gray-400">{catName[s.category_id] || "—"}</td>
            <td className="p-3"><RowActions id={s.id} onEdit={() => ed.openEdit(s)} onDelete={() => remove(s)} /></td>
          </tr>
        ))}
      </DataTable>
      <FormDialog open={ed.open} onOpenChange={ed.setOpen} title={ed.editingId ? "Edit subject" : "New subject"} onSubmit={submit} saving={ed.saving} testid="subject-dialog">
        <Field label="Name"><input value={ed.form.name} onChange={(e) => ed.set("name", e.target.value)} className={inputCls} data-testid="subject-name-input" /></Field>
        <Field label="Category"><CategorySelect value={ed.form.category_id} onChange={(v) => ed.set("category_id", v)} categories={cats} testid="subject-category-input" /></Field>
      </FormDialog>
    </div>
  );
}
