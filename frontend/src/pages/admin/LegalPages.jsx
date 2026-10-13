import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { PageHeader, DataTable, Pill, RowActions, NewButton, FormDialog, Field, inputCls, useEditor, errMsg } from "../../components/admin/kit";

const BLANK = { title: "", slug: "", content: "", published: true };

export default function LegalPages() {
  const [items, setItems] = useState([]);
  const ed = useEditor(BLANK);
  const f = ed.form;
  const load = () => api.get("/admin/pages").then((r) => setItems(r.data));
  useEffect(() => { load(); }, []);

  const submit = () => ed.run(async () => {
    if (ed.editingId) await api.put(`/admin/pages/${ed.editingId}`, f);
    else await api.post("/admin/pages", f);
    toast.success("Page saved");
    await load();
  });
  const remove = async (p) => {
    if (!window.confirm(`Delete page "${p.title}"?`)) return;
    try { await api.delete(`/admin/pages/${p.id}`); toast.success("Deleted"); load(); } catch (e) { toast.error(errMsg(e)); }
  };

  return (
    <div>
      <PageHeader eyebrow="System" title="Legal Pages" desc="Privacy, terms, refund, contact or any other page. Supports Markdown (## headings, **bold**, - lists)."
                  action={<NewButton onClick={ed.openNew} label="New page" testid="new-page-btn" />} />
      <DataTable testid="pages-table" head={["Title", "URL", "Status", "Updated", ""]} empty={!items.length && "No pages yet"}>
        {items.map((p) => (
          <tr key={p.id} className="border-t border-gray-800" data-testid={`page-row-${p.slug}`}>
            <td className="px-4 py-3 text-white">{p.title}</td>
            <td className="px-4 py-3 mono-font text-xs">
              <Link to={`/page/${p.slug}`} target="_blank" className="text-cyan-300 hover:underline inline-flex items-center gap-1">/page/{p.slug}<ExternalLink className="w-3 h-3" /></Link>
            </td>
            <td className="px-4 py-3">{p.published ? <Pill tone="emerald">PUBLISHED</Pill> : <Pill tone="gray">DRAFT</Pill>}</td>
            <td className="px-4 py-3 text-gray-400 text-xs">{new Date(p.updated_at).toLocaleString()}</td>
            <td className="px-4 py-3"><RowActions id={p.slug} onEdit={() => ed.openEdit(p)} onDelete={() => remove(p)} /></td>
          </tr>
        ))}
      </DataTable>

      <FormDialog open={ed.open} onOpenChange={ed.setOpen} title={ed.editingId ? "Edit page" : "New page"} onSubmit={submit} saving={ed.saving} testid="page-dialog" wide>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Title"><input required value={f.title} onChange={(e) => ed.set("title", e.target.value)} className={inputCls} data-testid="page-title-input" /></Field>
          <Field label="Slug (URL: /page/slug)"><input required value={f.slug} onChange={(e) => ed.set("slug", e.target.value)} className={`${inputCls} mono-font`} data-testid="page-slug-input" /></Field>
        </div>
        <Field label="Content (Markdown)">
          <textarea rows={14} value={f.content} onChange={(e) => ed.set("content", e.target.value)} className={`${inputCls} mono-font text-xs`} data-testid="page-content-input" />
        </Field>
        <label className="flex items-center gap-2 text-sm text-gray-300">
          <input type="checkbox" checked={f.published} onChange={(e) => ed.set("published", e.target.checked)} data-testid="page-published-checkbox" /> Published
        </label>
      </FormDialog>
    </div>
  );
}
