import React, { useEffect, useState } from "react";
import ImageField from "../../components/admin/ImageField";
import { PageHeader, Pill, RowActions, NewButton, FormDialog, Field, inputCls, CategorySelect, rupees, useResource, useEditor, useCategories } from "../../components/admin/kit";
import CourseEditor from "./CourseEditor";

const BLANK = { title: "", description: "", category_id: "", thumbnail: "", is_free: true, price_rupees: 0 };

export default function Courses() {
  const { items, loading, save, remove } = useResource("/courses", "courses");
  const cats = useCategories();
  const ed = useEditor(BLANK);
  const [selected, setSelected] = useState(null);
  const f = ed.form;

  useEffect(() => {
    if (!items.find((c) => c.id === selected)) setSelected(items[0]?.id || null);
  }, [items, selected]);

  const submit = () => ed.run(() => save(ed.editingId, {
    title: f.title, description: f.description, category_id: f.category_id || null, thumbnail: f.thumbnail || null,
    is_free: f.is_free, price: f.is_free ? 0 : Math.round(Number(f.price_rupees) * 100),
  }, "/courses"));

  return (
    <div>
      <PageHeader eyebrow="Content" title="Course builder" desc="Courses → sections → lessons. Pick a course to edit its curriculum."
                  action={<NewButton onClick={ed.openNew} label="New course" testid="new-course-btn" />} />
      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        <div className="space-y-2" data-testid="course-list">
          {items.map((c) => (
            <div key={c.id} onClick={() => setSelected(c.id)} data-testid={`course-item-${c.id}`}
                 className={`card-elev p-3 cursor-pointer ${selected === c.id ? "border-blue-500/60 bg-blue-500/5" : ""}`}>
              <div className="flex items-start gap-2">
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-white font-medium truncate">{c.title}</div>
                  <div className="mt-1.5">{c.is_free ? <Pill tone="emerald">FREE</Pill> : <Pill tone="amber">{rupees(c.price)}</Pill>}</div>
                </div>
                <div onClick={(e) => e.stopPropagation()}>
                  <RowActions id={c.id} onDelete={() => remove(c.id)}
                    onEdit={() => ed.openEdit(c, (x) => ({ ...x, category_id: x.category_id || "", thumbnail: x.thumbnail || "", price_rupees: (x.price || 0) / 100 }))} />
                </div>
              </div>
            </div>
          ))}
          {!loading && !items.length && <div className="card-elev p-6 text-sm text-gray-500 text-center">No courses yet.</div>}
        </div>
        <div>{selected ? <CourseEditor key={selected} courseId={selected} /> : <div className="text-gray-500 text-sm">Create a course to start building its curriculum.</div>}</div>
      </div>

      <FormDialog open={ed.open} onOpenChange={ed.setOpen} title={ed.editingId ? "Edit course" : "New course"} onSubmit={submit} saving={ed.saving} testid="course-form">
        <Field label="Title"><input required value={f.title} onChange={(e) => ed.set("title", e.target.value)} className={inputCls} data-testid="course-title-input" /></Field>
        <Field label="Description"><textarea rows={3} value={f.description} onChange={(e) => ed.set("description", e.target.value)} className={inputCls} data-testid="course-description-input" /></Field>
        <Field label="Category"><CategorySelect value={f.category_id} onChange={(v) => ed.set("category_id", v)} categories={cats} testid="course-category-input" /></Field>
        <ImageField label="Thumbnail" wide value={f.thumbnail} onChange={(v) => ed.set("thumbnail", v)} testid="course-thumbnail" hint="Recommended 16:9, e.g. 1280×720. PNG, JPG or WEBP up to 2 MB." />
        <label className="flex items-center gap-2 text-sm text-gray-300">
          <input type="checkbox" checked={f.is_free} onChange={(e) => ed.set("is_free", e.target.checked)} data-testid="course-free-input" /> Free course
        </label>
        <Field label="Price (₹)"><input type="number" min="0" disabled={f.is_free} value={f.price_rupees} onChange={(e) => ed.set("price_rupees", e.target.value)} className={`${inputCls} disabled:opacity-40`} data-testid="course-price-input" /></Field>
      </FormDialog>
    </div>
  );
}
