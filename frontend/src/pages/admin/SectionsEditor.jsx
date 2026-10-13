import React, { useState } from "react";
import { ChevronDown, ChevronUp, X } from "lucide-react";
import { inputCls } from "../../components/admin/kit";
import QuestionPicker from "./QuestionPicker";

const PRESETS = ["Quantitative Aptitude", "Reasoning Ability", "English Language", "General Awareness", "Computer Knowledge"];

export default function SectionsEditor({ sections, onChange, sectional, questions, categories }) {
  const [openIdx, setOpenIdx] = useState(0);
  const update = (i, patch) => onChange(sections.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const add = () => { onChange([...sections, { name: PRESETS[sections.length] || `Section ${sections.length + 1}`, duration_minutes: 20, question_ids: [] }]); setOpenIdx(sections.length); };
  const remove = (i) => onChange(sections.filter((_, j) => j !== i));
  const move = (i, d) => { const n = [...sections]; [n[i], n[i + d]] = [n[i + d], n[i]]; onChange(n); };
  const marksOf = (ids) => questions.filter((q) => ids.includes(q.id)).reduce((s, q) => s + (q.positive_marks || 0), 0);

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
                {s.question_ids.length} Q · {marksOf(s.question_ids)} M {openIdx === i ? "▲" : "▼"}
              </button>
              <div className="flex">
                <button type="button" disabled={i === 0} onClick={() => move(i, -1)} className="p-1 text-gray-500 hover:text-white disabled:opacity-30"><ChevronUp className="w-4 h-4" /></button>
                <button type="button" disabled={i === sections.length - 1} onClick={() => move(i, 1)} className="p-1 text-gray-500 hover:text-white disabled:opacity-30"><ChevronDown className="w-4 h-4" /></button>
                {sections.length > 1 && <button type="button" onClick={() => remove(i)} className="p-1 text-gray-500 hover:text-rose-300" data-testid={`section-remove-${i}`}><X className="w-4 h-4" /></button>}
              </div>
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
