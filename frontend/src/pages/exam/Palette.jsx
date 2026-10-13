import React from "react";
import { X } from "lucide-react";

const LEGEND = [
  ["qp-answered", "Answered"], ["qp-not-answered", "Not Answered"], ["qp-marked", "Marked for Review"],
  ["qp-ans-marked", "Answered & Marked"], ["qp-not-visited", "Not Visited"],
];
const pad = (n) => String(n).padStart(2, "0");

export const StatBoxes = ({ stats }) => (
  <div className="grid grid-cols-4 gap-1.5 text-center">
    {[["bg-emerald-500", stats.answered, "Answered", "stat-answered"], ["bg-rose-500", stats.notAnswered, "Not answered", "stat-not-answered"],
      ["bg-violet-500", stats.marked, "Review", "stat-marked"], ["bg-gray-500", stats.notVisited, "Not visited", "stat-not-visited"]].map(([dot, v, l, id]) => (
      <div key={l} className="rounded-md border border-gray-800 bg-[#111827] px-1 py-1.5">
        <div className="flex items-center justify-center gap-1 text-sm font-bold text-white"><span className={`w-2.5 h-2.5 rounded-sm ${dot}`} /><span data-testid={id}>{pad(v)}</span></div>
        <div className="text-[9px] text-gray-400 leading-tight mt-0.5">{l}</div>
      </div>
    ))}
  </div>
);

// groups: [{ name, minutes, items: [{ q, i }] }] — i is the global question index
export default function Palette({ groups, idx, statusOf, stats, open, onClose, onJump }) {
  let n = 0;
  return (
    <aside data-testid="palette-panel"
           className={`${open ? "fixed inset-0 z-50 flex" : "hidden"} lg:flex lg:static lg:z-auto lg:w-80 xl:w-96 flex-col bg-[#0b1120] lg:rounded-xl lg:border border-gray-800 lg:max-h-[calc(100vh-8rem)] lg:sticky lg:top-4`}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <div className="heading-font font-semibold text-white" data-testid="palette-title">Question palette</div>
        {open && <button onClick={onClose} className="lg:hidden p-1 text-gray-400 hover:text-white" aria-label="Close palette" data-testid="palette-close"><X /></button>}
      </div>
      <div className="p-3 border-b border-gray-800"><StatBoxes stats={stats} /></div>
      <div className="flex-1 overflow-y-auto p-4 space-y-5" data-testid="question-palette">
        {groups.map((g) => (
          <div key={g.name}>
            {groups.length > 1 || g.name ? (
              <div className="flex items-center justify-between mb-2 text-sm">
                <span className="font-semibold text-gray-200 truncate">{g.name || "Questions"}</span>
                {g.minutes ? <span className="mono-font text-[11px] text-gray-500">{g.minutes} min</span> : null}
              </div>
            ) : null}
            <div className="grid grid-cols-5 gap-2">
              {g.items.map(({ q, i }) => {
                n += 1;
                return (
                  <button key={q.id} onClick={() => onJump(i)} data-testid={`palette-q-${n}`}
                          className={`${statusOf(q)} ${i === idx ? "qp-current" : ""} w-full aspect-square rounded-md mono-font font-semibold text-sm transition-transform hover:scale-105`}>
                    {i + 1}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="px-4 py-3 border-t border-gray-800 grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11px] mono-font">
        {LEGEND.map(([c, l]) => (
          <div key={c} className="flex items-center gap-2"><span className={`w-3 h-3 rounded-sm inline-block shrink-0 ${c}`} /><span className="text-gray-400 truncate">{l}</span></div>
        ))}
      </div>
    </aside>
  );
}
