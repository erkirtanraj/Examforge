import React, { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { api } from "../../lib/api";
import { PageHeader, DataTable, Pill, RowActions, NewButton, FormDialog, Field, inputCls, useResource, useEditor, useCategories } from "../../components/admin/kit";
import QuestionPicker from "./QuestionPicker";

const BLANK = { series_id: "", title: "", duration_minutes: 60, passing_marks: "", instructions: "", is_published: true, question_ids: [] };

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

  const submit = () => {
    if (!f.series_id) return toast.error("Choose a test series");
    if (!f.question_ids.length) return toast.error("Pick at least one question");
    ed.run(() => save(ed.editingId, {
      series_id: f.series_id, title: f.title, duration_minutes: Number(f.duration_minutes),
      passing_marks: f.passing_marks === "" ? null : Number(f.passing_marks), instructions: f.instructions,
      is_published: f.is_published, question_ids: f.question_ids,
    }, "/tests"));
  };

  return (
    <div>
      <PageHeader eyebrow="Content" title="Test builder" desc="Pick questions from the bank, set the timer and publish."
                  action={<NewButton onClick={ed.openNew} label="New test" testid="new-test-btn" />} />
      <DataTable head={["Test", "Series", "Questions", "Duration", "Marks", "Status", ""]} testid="tests-table"
                 empty={!loading && !items.length ? "No tests yet." : null}>
        {items.map((t) => (
          <tr key={t.id} className="border-t border-gray-800 hover:bg-gray-900/40" data-testid={`test-row-${t.id}`}>
            <td className="p-3 text-white">{t.title}</td>
            <td className="p-3 text-gray-400 max-w-[220px] truncate">{seriesName[t.series_id] || "—"}</td>
            <td className="p-3 mono-font text-gray-300">{t.question_ids?.length || 0}</td>
            <td className="p-3 text-gray-300 whitespace-nowrap">{t.duration_minutes} min</td>
            <td className="p-3 mono-font text-gray-300">{t.total_marks}</td>
            <td className="p-3">{t.is_published ? <Pill tone="emerald">LIVE</Pill> : <Pill tone="gray">DRAFT</Pill>}</td>
            <td className="p-3"><RowActions id={t.id} onDelete={() => remove(t.id)}
                  onEdit={() => ed.openEdit(t, (x) => ({ ...x, passing_marks: x.passing_marks ?? "", instructions: x.instructions || "" }))} /></td>
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
          <Field label="Duration (minutes)"><input type="number" min="1" value={f.duration_minutes} onChange={(e) => ed.set("duration_minutes", e.target.value)} className={inputCls} data-testid="test-duration-input" /></Field>
          <Field label="Passing marks (optional)"><input type="number" min="0" value={f.passing_marks} onChange={(e) => ed.set("passing_marks", e.target.value)} className={inputCls} data-testid="test-passing-input" /></Field>
        </div>
        <Field label="Instructions"><textarea rows={2} value={f.instructions} onChange={(e) => ed.set("instructions", e.target.value)} className={inputCls} data-testid="test-instructions-input" /></Field>
        <label className="flex items-center gap-2 text-sm text-gray-300">
          <input type="checkbox" checked={f.is_published} onChange={(e) => ed.set("is_published", e.target.checked)} data-testid="test-published-input" /> Published
        </label>
        <div>
          <div className="text-[11px] text-gray-400 mono-font uppercase tracking-wider mb-1.5">Questions</div>
          <QuestionPicker questions={questions} categories={cats} selected={f.question_ids} onChange={(ids) => ed.set("question_ids", ids)} />
        </div>
      </FormDialog>
    </div>
  );
}
