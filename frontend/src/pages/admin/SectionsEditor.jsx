import React, { useState } from "react";
import { ChevronDown, ChevronUp, X } from "lucide-react";
import { inputCls } from "../../components/admin/kit";
import QuestionPicker from "./QuestionPicker";

const PRESETS = ["Quantitative Aptitude", "Reasoning Ability", "English Language", "General Awareness", "Computer Knowledge"];

export default function SectionsEditor({ sections, onChange, sectional, questions, categories }) {
  const [openIdx, setOpenIdx] = useState(0);
  const update = (i, patch) => onChange(sections.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const add = () => { onChange([...sections, { name: PRESETS[sections.length] || `Section ${sections.length + 1}`, duration_minutes: 20, question_ids: [], positive_marks: null, negative_marks: null, language: "bilingual" }]); setOpenIdx(sections.length); };
  const remove = (i) => onChange(sections.filter((_, j) => j !== i));
  const move = (i, d) => { const n = [...sections]; [n[i], n[i + d]] = [n[i + d], n[i]]; onChange(n); };
  const marksOf = (sec) => questions.filter((q) => sec.question_ids.includes(q.id))
    .reduce((t, q) => t + (sec.positive_marks != null && sec.positive_marks !== "" ? Number(sec.positive_marks) : q.positive_marks || 0), 0);
  const num = (v) => (v === "" ? null : Number(v));

  return (
    <div className="space-y-2" data-testid="sections-editor">
      <datalist id="section-presets">{PRESETS.map((p) => <option key={p} value={p} />)}</datalist>
      {sections.map((s, i) => {
        const used = new Set(sections.flatMap((x, j) => (j === i ? [] : x.question_ids)));
        return (
          <div key={i} className={`rounded-md border ${openIdx === i ? "border-blue-500/50" : "border-gray-800"}`} data-testid={`section-editor-${i}`}>
            <div className="flex flex-wrap items-center gap-2 p-2">
              <span className="mono-font text-xs text-gray-500 w-5 text-center">{i + 1}</span>
              <input list="section-presets" value={s.name} onChange={(e) => update(i, { name: e.target.value })} placeholder="Section name"
                     className={`${inputCls} mt-0 flex-1 min-w-[160px]`} data-testid={`section-name-${i}`} />
              {sectional && (
                <div className="flex items-center gap-1">
                  <input type="number" min="1" value={s.duration_minutes ?? ""} onChange={(e) => update(i, { duration_minutes: e.target.value === "" ? null : Number(e.target.value) })}
                         className={`${inputCls} mt-0 w-20`} data-testid={`section-duration-${i}`} />
                  <span className="text-xs text-gray-500">min</span>
                </div>
              )}
              <button type="button" onClick={() => setOpenIdx(openIdx === i ? -1 : i)} data-testid={`section-toggle-${i}`}
                      className="text-xs mono-font px-2 py-1.5 rounded border border-gray-700 text-gray-300 hover:bg-gray-800 whitespace-nowrap">
                {s.question_ids.length} Q · {+marksOf(s).toFixed(2)} M {openIdx === i ? "▲" : "▼"}
              </button>
              <div className="flex">
                <button type="button" disabled={i === 0} onClick={() => move(i, -1)} className="p-1 text-gray-500 hover:text-white disabled:opacity-30"><ChevronUp className="w-4 h-4" /></button>
                <button type="button" disabled={i === sections.length - 1} onClick={() => move(i, 1)} className="p-1 text-gray-500 hover:text-white disabled:opacity-30"><ChevronDown className="w-4 h-4" /></button>
                {sections.length > 1 && <button type="button" onClick={() => remove(i)} className="p-1 text-gray-500 hover:text-rose-300" data-testid={`section-remove-${i}`}><X className="w-4 h-4" /></button>}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-2 pb-2 pl-9 text-xs text-gray-400" data-testid={`section-rules-${i}`}>
              <label className="flex items-center gap-1.5 normal-case tracking-normal">
                <span className="text-emerald-300 mono-font">+</span> Marks / correct
                <input type="number" step="0.25" min="0" placeholder="Q's own" value={s.positive_marks ?? ""} onChange={(e) => update(i, { positive_marks: num(e.target.value) })}
                       className={`${inputCls} mt-0 w-24 py-1`} data-testid={`section-positive-${i}`} />
              </label>
              <label className="flex items-center gap-1.5 normal-case tracking-normal">
                <span className="text-rose-300 mono-font">−</span> Negative / wrong
                <input type="number" step="0.25" min="0" placeholder="Q's own" value={s.negative_marks ?? ""} onChange={(e) => update(i, { negative_marks: num(e.target.value) })}
                       className={`${inputCls} mt-0 w-24 py-1`} data-testid={`section-negative-${i}`} />
              </label>
              <label className="flex items-center gap-1.5 normal-case tracking-normal">
                Language
                <select value={s.language || "bilingual"} onChange={(e) => update(i, { language: e.target.value })} className={`${inputCls} mt-0 w-auto py-1`} data-testid={`section-language-${i}`}>
                  <option value="bilingual">Bilingual (students can switch)</option>
                  <option value="en">English only</option>
                  <option value="hi">Hindi only</option>
                </select>
              </label>
            </div>
            {openIdx === i && (
              <div className="p-2 pt-0">
                <QuestionPicker questions={questions.filter((q) => !used.has(q.id))} categories={categories}
                                selected={s.question_ids} onChange={(ids) => update(i, { question_ids: ids })} />
              </div>
            )}
          </div>
        );
      })}
      <button type="button" onClick={add} className="text-xs text-blue-400 hover:text-blue-300" data-testid="add-section-btn">+ Add section</button>
    </div>
  );
}
