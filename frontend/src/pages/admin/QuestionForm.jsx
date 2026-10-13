import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { X } from "lucide-react";
import { FormDialog, Field, inputCls, CategorySelect, SubjectSelect, errMsg } from "../../components/admin/kit";
import LangToggle from "../../components/LangToggle";

const KEYS = "ABCDEFGH".split("");
const blankQ = () => ({
  text: "", text_hi: "", type: "mcq_single", options: KEYS.slice(0, 4).map((k) => ({ key: k, text: "", text_hi: "" })), correct: [],
  explanation: "", explanation_hi: "", category_id: "", subject_id: "", difficulty: "medium", language: "en", positive_marks: 1, negative_marks: 0, image_url: "",
});
const TF = [{ key: "A", text: "True", text_hi: "सत्य" }, { key: "B", text: "False", text_hi: "असत्य" }];

export default function QuestionForm({ open, onOpenChange, initial, categories, subjects = [], onSave }) {
  const [f, setF] = useState(blankQ());
  const [saving, setSaving] = useState(false);
  const [lang, setLang] = useState("en");
  const tk = lang === "hi" ? "text_hi" : "text";
  const ek = lang === "hi" ? "explanation_hi" : "explanation";

  useEffect(() => {
    if (open) setLang("en");
    if (open) setF(initial ? { ...blankQ(), ...initial, text_hi: initial.text_hi || "", explanation_hi: initial.explanation_hi || "", category_id: initial.category_id || "", subject_id: initial.subject_id || "", image_url: initial.image_url || "" } : blankQ());
  }, [open, initial]);

  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const changeType = (t) => setF((p) => ({
    ...p, type: t, correct: [],
    options: t === "true_false" ? TF : t === "numerical" ? [] : p.type === "true_false" || !p.options.length ? blankQ().options : p.options,
  }));
  const toggleCorrect = (k) => setF((p) => ({
    ...p, correct: p.type === "mcq_multi" ? (p.correct.includes(k) ? p.correct.filter((x) => x !== k) : [...p.correct, k]) : [k],
  }));
  const setOpt = (i, v) => setF((p) => ({ ...p, options: p.options.map((o, j) => (j === i ? { ...o, [tk]: v } : o)) }));
  const addOpt = () => setF((p) => (p.options.length < 8 ? { ...p, options: [...p.options, { key: KEYS[p.options.length], text: "" }] } : p));
  const removeOpt = (i) => setF((p) => ({ ...p, correct: [], options: p.options.filter((_, j) => j !== i).map((o, j) => ({ ...o, key: KEYS[j] })) }));

  const submit = async () => {
    if (!f.text.trim()) return toast.error("Enter the question text");
    if (!f.correct.length || f.correct[0] === "") return toast.error("Mark the correct answer");
    if (f.type !== "numerical" && f.options.some((o) => !o.text.trim())) return toast.error("Fill in every option");
    setSaving(true);
    try {
      await onSave({ ...f, category_id: f.category_id || null, subject_id: f.subject_id || null, image_url: f.image_url || null,
        text_hi: f.text_hi?.trim() || null, explanation_hi: f.explanation_hi?.trim() || null,
        options: f.options.map((o) => ({ ...o, text_hi: o.text_hi?.trim() || null })),
        positive_marks: Number(f.positive_marks), negative_marks: Number(f.negative_marks) });
      onOpenChange(false);
    } catch (e) { toast.error(errMsg(e)); } finally { setSaving(false); }
  };

  const choice = f.type !== "numerical";
  return (
    <FormDialog open={open} onOpenChange={onOpenChange} title={initial ? "Edit question" : "New question"}
                onSubmit={submit} saving={saving} testid="question-form" wide>
      <div className="flex items-center justify-between gap-3 -mt-1">
        <span className="text-xs text-gray-500">{lang === "hi" ? "Hindi is optional — students fall back to English where it's blank." : "English is required."}</span>
        <LangToggle lang={lang} onChange={setLang} testid="q-lang" />
      </div>
      <Field label={lang === "hi" ? "Question (हिन्दी)" : "Question"}>
        <textarea rows={3} value={f[tk] || ""} onChange={(e) => set(tk, e.target.value)} className={inputCls} data-testid={lang === "hi" ? "q-text-hi" : "q-text"} />
      </Field>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <Field label="Type">
          <select value={f.type} onChange={(e) => changeType(e.target.value)} className={inputCls} data-testid="q-type">
            <option value="mcq_single">MCQ · single answer</option>
            <option value="mcq_multi">MCQ · multiple answers</option>
            <option value="true_false">True / False</option>
            <option value="numerical">Numerical</option>
          </select>
        </Field>
        <Field label="Category">
          <CategorySelect value={f.category_id} onChange={(v) => setF((p) => ({ ...p, category_id: v, subject_id: subjects.find((s) => s.id === p.subject_id)?.category_id === v ? p.subject_id : "" }))} categories={categories} testid="q-category" />
        </Field>
        <Field label="Subject">
          <SubjectSelect value={f.subject_id} onChange={(v) => setF((p) => ({ ...p, subject_id: v, category_id: p.category_id || subjects.find((s) => s.id === v)?.category_id || "" }))} subjects={subjects} categoryId={f.category_id} testid="q-subject" />
        </Field>
        <Field label="Difficulty">
          <select value={f.difficulty} onChange={(e) => set("difficulty", e.target.value)} className={inputCls} data-testid="q-difficulty">
            <option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option>
          </select>
        </Field>
      </div>

      {choice ? (
        <div>
          <div className="text-[11px] text-gray-400 mono-font uppercase tracking-wider mb-1.5">
            Options · tick the correct {f.type === "mcq_multi" ? "answers" : "answer"}
          </div>
          <div className="space-y-2">
            {f.options.map((o, i) => (
              <div key={o.key} className={`flex items-center gap-2 p-1.5 rounded-md border ${f.correct.includes(o.key) ? "border-emerald-500/50 bg-emerald-500/5" : "border-gray-800"}`}>
                <button type="button" onClick={() => toggleCorrect(o.key)} data-testid={`q-correct-${o.key}`}
                        className={`w-8 h-8 shrink-0 rounded mono-font text-sm font-semibold transition-colors ${f.correct.includes(o.key) ? "bg-emerald-500 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700"}`}>
                  {o.key}
                </button>
                <input value={o[tk] || ""} onChange={(e) => setOpt(i, e.target.value)} disabled={f.type === "true_false"}
                       className="flex-1 bg-transparent border-0 text-sm text-white focus:outline-none" placeholder={lang === "hi" ? `${o.text || `Option ${o.key}`} (हिन्दी)` : `Option ${o.key}`} data-testid={lang === "hi" ? `q-option-hi-${o.key}` : `q-option-${o.key}`} />
                {f.type !== "true_false" && f.options.length > 2 && (
                  <button type="button" onClick={() => removeOpt(i)} className="p-1 text-gray-500 hover:text-rose-300"><X className="w-4 h-4" /></button>
                )}
              </div>
            ))}
          </div>
          {f.type !== "true_false" && f.options.length < 8 && (
            <button type="button" onClick={addOpt} className="mt-2 text-xs text-blue-400 hover:text-blue-300" data-testid="q-add-option">+ Add option</button>
          )}
        </div>
      ) : (
        <Field label="Correct numerical answer">
          <input type="number" step="any" value={f.correct[0] ?? ""} onChange={(e) => set("correct", [e.target.value])} className={inputCls} data-testid="q-numeric-answer" />
        </Field>
      )}

      <div className="grid grid-cols-2 gap-3">
        <Field label="Marks (+)">
          <input type="number" step="0.25" min="0" value={f.positive_marks} onChange={(e) => set("positive_marks", e.target.value)} className={inputCls} data-testid="q-positive" />
        </Field>
        <Field label="Negative marks (−)">
          <input type="number" step="0.25" min="0" value={f.negative_marks} onChange={(e) => set("negative_marks", e.target.value)} className={inputCls} data-testid="q-negative" />
        </Field>
      </div>
      <Field label="Explanation (shown after submission)">
        <textarea rows={2} value={f[ek] || ""} onChange={(e) => set(ek, e.target.value)} className={inputCls} data-testid={lang === "hi" ? "q-explanation-hi" : "q-explanation"} />
      </Field>
      <Field label="Image URL (optional)">
        <input value={f.image_url} onChange={(e) => set("image_url", e.target.value)} className={inputCls} data-testid="q-image" />
      </Field>
    </FormDialog>
  );
}
