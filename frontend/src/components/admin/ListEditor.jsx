import React from "react";
import { Plus, Trash2, ArrowUp, ArrowDown } from "lucide-react";
import { inputCls } from "./kit";

// Generic repeatable-row editor. fields: [{ key, placeholder, type?: "select", options? }]
export default function ListEditor({ items, onChange, fields, blank, testid, max, addLabel = "Add" }) {
  const update = (i, k, v) => onChange(items.map((it, j) => (j === i ? { ...it, [k]: v } : it)));
  const move = (i, d) => {
    const next = [...items];
    [next[i], next[i + d]] = [next[i + d], next[i]];
    onChange(next);
  };
  return (
    <div className="space-y-2" data-testid={testid}>
      {items.map((it, i) => (
        <div key={i} className="flex flex-wrap sm:flex-nowrap gap-2 items-center">
          {fields.map((f) => f.type === "select" ? (
            <select key={f.key} value={it[f.key]} onChange={(e) => update(i, f.key, e.target.value)} className={`${inputCls} mt-0 sm:w-40`} data-testid={`${testid}-${i}-${f.key}`}>
              {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          ) : (
            <input key={f.key} value={it[f.key]} placeholder={f.placeholder} onChange={(e) => update(i, f.key, e.target.value)}
                   className={`${inputCls} mt-0 ${f.wide ? "sm:flex-[2]" : "sm:flex-1"}`} data-testid={`${testid}-${i}-${f.key}`} />
          ))}
          <div className="flex gap-1 shrink-0">
            <button type="button" disabled={i === 0} onClick={() => move(i, -1)} className="p-2 rounded text-gray-400 hover:text-white disabled:opacity-30" data-testid={`${testid}-${i}-up`}><ArrowUp className="w-4 h-4" /></button>
            <button type="button" disabled={i === items.length - 1} onClick={() => move(i, 1)} className="p-2 rounded text-gray-400 hover:text-white disabled:opacity-30" data-testid={`${testid}-${i}-down`}><ArrowDown className="w-4 h-4" /></button>
            <button type="button" onClick={() => onChange(items.filter((_, j) => j !== i))} className="p-2 rounded text-gray-400 hover:text-rose-400" data-testid={`${testid}-${i}-remove`}><Trash2 className="w-4 h-4" /></button>
          </div>
        </div>
      ))}
      {(!max || items.length < max) && (
        <button type="button" onClick={() => onChange([...items, { ...blank }])} className="flex items-center gap-1 text-sm text-cyan-300 hover:text-cyan-200" data-testid={`${testid}-add`}>
          <Plus className="w-4 h-4" /> {addLabel}
        </button>
      )}
    </div>
  );
}
