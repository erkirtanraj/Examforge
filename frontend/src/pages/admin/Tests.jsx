import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { api } from "../../lib/api";
import { PageHeader, DataTable, Pill, RowActions, NewButton, FormDialog, Field, inputCls, useResource, useEditor, useCategories } from "../../components/admin/kit";
import SectionsEditor from "./SectionsEditor";

const BLANK = { series_id: "", title: "", duration_minutes: 60, passing_marks: "", instructions: "", is_published: true, sectional_timing: false, sections: [{ name: "General", duration_minutes: null, question_ids: [] }] };
const toForm = (t) => ({
  ...t, passing_marks: t.passing_marks ?? "", instructions: t.instructions || "", sectional_timing: !!t.sectional_timing,
  sections: t.sections?.length ? t.sections : [{ name: "General", duration_minutes: null, question_ids: t.question_ids || [] }],
});

export default function Tests() {
  const { items, loading, save, remove } = useResource("/admin/tests", "tests");
  const cats = useCategories();
  const [series, setSeries] = useState([]);
  const [questions, setQuestions] = useState([]);
  const ed = useEditor(BLANK);
  const f = ed.form;

  useEffect(() => {
    api.get("/test-series").then((r) => setSeries(r.data));
    api.get("/questions").then((r) => setQuestions(r.data));
  }, []);
  const seriesName = useMemo(() => Object.fromEntries(series.map((s) => [s.id, s.title])), [series]);

  const sectionTotal = f.sections.reduce((s, x) => s + (Number(x.duration_minutes) || 0), 0);
  const submit = () => {
    if (!f.series_id) return toast.error("Choose a test series");
    if (!f.sections.some((s) => s.question_ids.length)) return toast.error("Pick at least one question");
    if (f.sectional_timing && f.sections.some((s) => s.question_ids.length && !(Number(s.duration_minutes) > 0))) return toast.error("Give every section a duration");
    ed.run(() => save(ed.editingId, {
      series_id: f.series_id, title: f.title, duration_minutes: f.sectional_timing ? sectionTotal : Number(f.duration_minutes),
      passing_marks: f.passing_marks === "" ? null : Number(f.passing_marks), instructions: f.instructions,
      is_published: f.is_published, sectional_timing: f.sectional_timing,
      sections: f.sections.map((s) => ({ name: s.name, duration_minutes: s.duration_minutes ? Number(s.duration_minutes) : null, question_ids: s.question_ids })),
      question_ids: f.sections.flatMap((s) => s.question_ids),
    }, "/tests"));
  };

  return (
    <div>
      <PageHeader eyebrow="Content" title="Test builder" desc="Pick questions from the bank, set the timer and publish."
                  action={<NewButton onClick={ed.openNew} label="New test" testid="new-test-btn" />} />
      <DataTable head={["Test", "Series", "Questions", "Sections", "Duration", "Marks", "Status", ""]} testid="tests-table"
                 empty={!loading && !items.length ? "No tests yet." : null}>
        {items.map((t) => (
          <tr key={t.id} className="border-t border-gray-800 hover:bg-gray-900/40" data-testid={`test-row-${t.id}`}>
            <td className="p-3 text-white">{t.title}</td>
            <td className="p-3 text-gray-400 max-w-[220px] truncate">{seriesName[t.series_id] || "—"}</td>
            <td className="p-3 mono-font text-gray-300">{t.question_ids?.length || 0}</td>
            <td className="p-3 whitespace-nowrap">
              {t.sections?.length > 1 ? <span className="text-gray-300 mono-font text-xs">{t.sections.length} {t.sectional_timing && <Pill tone="blue">TIMED</Pill>}</span> : <span className="text-gray-600">—</span>}
            </td>
            <td className="p-3 text-gray-300 whitespace-nowrap">{t.duration_minutes} min</td>
            <td className="p-3 mono-font text-gray-300">{t.total_marks}</td>
            <td className="p-3">{t.is_published ? <Pill tone="emerald">LIVE</Pill> : <Pill tone="gray">DRAFT</Pill>}</td>
            <td className="p-3"><RowActions id={t.id} onDelete={() => remove(t.id)}
                  onEdit={() => ed.openEdit(t, toForm)} /></td>
          </tr>
        ))}
      </DataTable>

      <FormDialog open={ed.open} onOpenChange={ed.setOpen} title={ed.editingId ? "Edit test" : "New test"}
                  onSubmit={submit} saving={ed.saving} testid="test-form" wide>
        <div className="grid sm:grid-cols-2 gap-3">
          <Field label="Test series">
            <select value={f.series_id} onChange={(e) => ed.set("series_id", e.target.value)} className={inputCls} data-testid="test-series-input">
              <option value="">— Choose —</option>
              {series.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
            </select>
          </Field>
          <Field label="Title"><input required value={f.title} onChange={(e) => ed.set("title", e.target.value)} className={inputCls} data-testid="test-title-input" /></Field>
          <Field label={f.sectional_timing ? "Duration (sum of sections)" : "Duration (minutes)"}><input type="number" min="1" disabled={f.sectional_timing} value={f.sectional_timing ? sectionTotal : f.duration_minutes} onChange={(e) => ed.set("duration_minutes", e.target.value)} className={`${inputCls} disabled:opacity-60`} data-testid="test-duration-input" /></Field>
          <Field label="Passing marks (optional)"><input type="number" min="0" value={f.passing_marks} onChange={(e) => ed.set("passing_marks", e.target.value)} className={inputCls} data-testid="test-passing-input" /></Field>
        </div>
        <Field label="Instructions"><textarea rows={2} value={f.instructions} onChange={(e) => ed.set("instructions", e.target.value)} className={inputCls} data-testid="test-instructions-input" /></Field>
        <div className="flex flex-wrap gap-6">
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" checked={f.is_published} onChange={(e) => ed.set("is_published", e.target.checked)} data-testid="test-published-input" /> Published
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" checked={f.sectional_timing} data-testid="test-sectional-input"
                   onChange={(e) => ed.setForm((p) => ({ ...p, sectional_timing: e.target.checked, sections: p.sections.map((s) => ({ ...s, duration_minutes: s.duration_minutes || 20 })) }))} />
            Separate timer per section <span className="text-xs text-gray-500">(students can't return to a finished section)</span>
          </label>
        </div>
        <div>
          <div className="text-[11px] text-gray-400 mono-font uppercase tracking-wider mb-1.5">Sections &amp; questions</div>
          <SectionsEditor sections={f.sections} onChange={(s) => ed.set("sections", s)} sectional={f.sectional_timing} questions={questions} categories={cats} />
        </div>
      </FormDialog>
    </div>
  );
}
