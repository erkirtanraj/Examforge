import React, { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { PlayCircle, FileText, AlignLeft, Plus } from "lucide-react";
import { api } from "../../lib/api";
import { FormDialog, Field, inputCls, RowActions, errMsg, useEditor } from "../../components/admin/kit";

const BLANK_LESSON = { section_id: "", title: "", content_type: "video", content_url: "", text_content: "", position: 1, duration_minutes: 10 };
const ICON = { video: PlayCircle, pdf: FileText, text: AlignLeft };

export default function CourseEditor({ courseId }) {
  const [course, setCourse] = useState(null);
  const [newSection, setNewSection] = useState("");
  const ed = useEditor(BLANK_LESSON);
  const f = ed.form;

  const load = useCallback(() => api.get(`/courses/${courseId}`).then((r) => setCourse(r.data)), [courseId]);
  useEffect(() => { load(); }, [load]);

  const call = async (fn, msg) => {
    try { await fn(); if (msg) toast.success(msg); await load(); } catch (e) { toast.error(errMsg(e)); }
  };
  const addSection = (e) => {
    e.preventDefault();
    if (!newSection.trim()) return;
    call(() => api.post("/sections", { course_id: courseId, title: newSection.trim(), position: (course.sections?.length || 0) + 1 }), "Section added")
      .then(() => setNewSection(""));
  };
  const renameSection = (s) => {
    const title = window.prompt("Section title", s.title);
    if (title && title.trim()) call(() => api.put(`/content/sections/${s.id}`, { course_id: courseId, title: title.trim(), position: s.position }));
  };
  const del = (kind, id) => window.confirm("Delete this item? This cannot be undone.") && call(() => api.delete(`/content/${kind}/${id}`), "Deleted");
  const newLesson = (s) => { ed.openNew(); ed.setForm({ ...BLANK_LESSON, section_id: s.id, position: (s.lessons?.length || 0) + 1 }); };
  const submitLesson = () => ed.run(async () => {
    const payload = { ...f, position: Number(f.position), duration_minutes: Number(f.duration_minutes), content_url: f.content_url || null };
    if (ed.editingId) await api.put(`/content/lessons/${ed.editingId}`, payload);
    else await api.post("/lessons", payload);
    toast.success("Lesson saved");
    await load();
  });

  if (!course) return <div className="text-gray-400 text-sm">Loading course…</div>;
  return (
    <div className="space-y-4" data-testid="course-editor">
      {course.sections?.map((s) => (
        <div key={s.id} className="card-elev" data-testid={`section-${s.id}`}>
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
            <div className="heading-font font-semibold text-white">{s.title}</div>
            <div className="flex items-center gap-1">
              <button onClick={() => newLesson(s)} data-testid={`add-lesson-${s.id}`} className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 px-2 py-1"><Plus className="w-3.5 h-3.5" />Lesson</button>
              <RowActions id={`section-${s.id}`} onEdit={() => renameSection(s)} onDelete={() => del("sections", s.id)} />
            </div>
          </div>
          <div className="divide-y divide-gray-800/70">
            {s.lessons?.map((l) => {
              const Icon = ICON[l.content_type] || PlayCircle;
              return (
                <div key={l.id} className="flex items-center gap-3 px-4 py-2.5 text-sm" data-testid={`lesson-row-${l.id}`}>
                  <Icon className="w-4 h-4 text-cyan-300 shrink-0" />
                  <span className="flex-1 text-gray-200 truncate">{l.title}</span>
                  <span className="text-xs mono-font text-gray-500">{l.duration_minutes}m</span>
                  <RowActions id={`lesson-${l.id}`} onEdit={() => ed.openEdit(l, (x) => ({ ...x, content_url: x.content_url || "", text_content: x.text_content || "" }))} onDelete={() => del("lessons", l.id)} />
                </div>
              );
            })}
            {!s.lessons?.length && <div className="px-4 py-3 text-xs text-gray-500">No lessons yet.</div>}
          </div>
        </div>
      ))}
      <form onSubmit={addSection} className="flex gap-2">
        <input value={newSection} onChange={(e) => setNewSection(e.target.value)} placeholder="New section title, e.g. Module 3: Algebra"
               className={`${inputCls} mt-0`} data-testid="new-section-input" />
        <button type="submit" className="btn-primary text-sm whitespace-nowrap" data-testid="add-section-btn">Add section</button>
      </form>

      <FormDialog open={ed.open} onOpenChange={ed.setOpen} title={ed.editingId ? "Edit lesson" : "New lesson"} onSubmit={submitLesson} saving={ed.saving} testid="lesson-form">
        <Field label="Title"><input required value={f.title} onChange={(e) => ed.set("title", e.target.value)} className={inputCls} data-testid="lesson-title-input" /></Field>
        <div className="grid grid-cols-3 gap-3">
          <Field label="Type">
            <select value={f.content_type} onChange={(e) => ed.set("content_type", e.target.value)} className={inputCls} data-testid="lesson-type-input">
              <option value="video">Video</option><option value="pdf">PDF</option><option value="text">Text</option>
            </select>
          </Field>
          <Field label="Order"><input type="number" min="1" value={f.position} onChange={(e) => ed.set("position", e.target.value)} className={inputCls} data-testid="lesson-position-input" /></Field>
          <Field label="Minutes"><input type="number" min="0" value={f.duration_minutes} onChange={(e) => ed.set("duration_minutes", e.target.value)} className={inputCls} data-testid="lesson-duration-input" /></Field>
        </div>
        {f.content_type !== "text" && (
          <Field label={f.content_type === "video" ? "Video embed URL (YouTube/Vimeo embed link)" : "PDF URL"}>
            <input value={f.content_url} onChange={(e) => ed.set("content_url", e.target.value)} className={inputCls} data-testid="lesson-url-input" />
          </Field>
        )}
        <Field label="Notes / text content"><textarea rows={3} value={f.text_content} onChange={(e) => ed.set("text_content", e.target.value)} className={inputCls} data-testid="lesson-text-input" /></Field>
      </FormDialog>
    </div>
  );
}
