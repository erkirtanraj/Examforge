import React, { useState } from "react";
import { inputCls, CategorySelect } from "../../components/admin/kit";

export default function QuestionPicker({ questions, categories, selected, onChange }) {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("");
  const sel = new Set(selected);
  const visible = questions
    .filter((x) => (!cat || x.category_id === cat) && x.text.toLowerCase().includes(q.toLowerCase()))
    .sort((a, b) => sel.has(b.id) - sel.has(a.id));
  const toggle = (id) => onChange(sel.has(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  const addAll = () => onChange([...selected, ...visible.map((x) => x.id).filter((id) => !sel.has(id))]);
  const marks = questions.filter((x) => sel.has(x.id)).reduce((s, x) => s + (x.positive_marks || 0), 0);

  return (
    <div className="rounded-md border border-gray-800">
      <div className="p-3 border-b border-gray-800 grid sm:grid-cols-2 gap-2">
        <input placeholder="Search questions…" value={q} onChange={(e) => setQ(e.target.value)} className={`${inputCls} mt-0`} data-testid="picker-search" />
        <CategorySelect value={cat} onChange={setCat} categories={categories} allowAll testid="picker-category" />
      </div>
      <div className="flex items-center justify-between px-3 py-2 text-xs mono-font text-gray-400 border-b border-gray-800">
        <span data-testid="picker-summary">{selected.length} SELECTED · {marks} MARKS</span>
        <span className="space-x-3">
          <button type="button" onClick={addAll} className="text-blue-400 hover:text-blue-300" data-testid="picker-select-all">Select shown</button>
          <button type="button" onClick={() => onChange([])} className="text-gray-400 hover:text-white" data-testid="picker-clear">Clear</button>
        </span>
      </div>
      <div className="max-h-64 overflow-y-auto divide-y divide-gray-800/70">
        {visible.map((x) => (
          <label key={x.id} className="flex items-start gap-3 p-3 text-sm cursor-pointer hover:bg-gray-900/50 normal-case tracking-normal">
            <input type="checkbox" checked={sel.has(x.id)} onChange={() => toggle(x.id)} className="mt-1" data-testid={`picker-q-${x.id}`} />
            <span className="flex-1 text-gray-200">{x.text}</span>
            <span className="mono-font text-xs text-emerald-300 shrink-0">+{x.positive_marks}</span>
          </label>
        ))}
        {!visible.length && <div className="p-6 text-center text-sm text-gray-500">No questions found. Add some in the Question Bank.</div>}
      </div>
    </div>
  );
}
