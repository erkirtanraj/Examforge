import React from "react";
import { X } from "lucide-react";

const LEGEND = [
  ["qp-answered", "Answered"], ["qp-not-answered", "Not Answered"], ["qp-marked", "Marked for Review"],
  ["qp-ans-marked", "Answered & Marked"], ["qp-not-visited", "Not Visited"],
];

export const StatBoxes = ({ stats }) => (
  <div className="grid grid-cols-3 gap-2 text-center">
    {[["emerald", stats.answered, "ANSWERED", "stat-answered"], ["violet", stats.marked, "MARKED", "stat-marked"], ["gray", stats.notVisited, "NOT VISITED", "stat-not-visited"]].map(([c, v, l, id]) => (
      <div key={l} className={`rounded-md p-2 border ${c === "gray" ? "bg-gray-700/30 border-gray-700" : `bg-${c}-500/10 border-${c}-500/30`}`}>
        <div className={`text-xl font-bold ${c === "gray" ? "text-gray-300" : `text-${c}-300`}`} data-testid={id}>{v}</div>
        <div className="text-[10px] text-gray-400 mono-font">{l}</div>
      </div>
    ))}
  </div>
);

// items: [{ q, i }] — questions shown in the palette with their global index
export default function Palette({ title, items, idx, statusOf, stats, open, onClose, onJump }) {
  return (
    <aside className={`${open ? "fixed inset-0 z-50 bg-[#0b1120] overflow-auto" : "hidden"} lg:static lg:block lg:w-80 border-l border-gray-800 bg-[#0b1120]`}>
      <div className="p-4">
        {open && <button onClick={onClose} className="lg:hidden mb-3 text-gray-400"><X /></button>}
        <div className="text-sm text-gray-400 mono-font uppercase mb-2">Progress</div>
        <StatBoxes stats={stats} />
        <div className="text-sm text-gray-400 mono-font uppercase mt-4 mb-2 truncate" data-testid="palette-title">{title}</div>
        <div className="grid grid-cols-5 gap-2" data-testid="question-palette">
          {items.map(({ q, i }, n) => (
            <button key={q.id} onClick={() => onJump(i)} data-testid={`palette-q-${n + 1}`}
                    className={`${statusOf(q)} ${i === idx ? "qp-current" : ""} w-full aspect-square rounded mono-font font-semibold text-sm`}>
              {n + 1}
            </button>
          ))}
        </div>
        <div className="mt-4 text-[11px] mono-font space-y-1.5">
          {LEGEND.map(([c, l]) => (
            <div key={c} className="flex items-center gap-2"><span className={`w-3 h-3 rounded-sm inline-block ${c}`} /><span className="text-gray-400">{l}</span></div>
          ))}
        </div>
      </div>
    </aside>
  );
}
