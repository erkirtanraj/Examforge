import React from "react";
import { Check, Lock } from "lucide-react";
import { isAnswered } from "./useCountdown";

// Free mode: clickable tabs. Sectional mode: read-only stepper (done / current / locked).
export default function SectionBar({ sections, sectional, current, active, answers, onSelect }) {
  if (!sections || sections.length < 2) return null;
  return (
    <div className="border-b border-gray-800 bg-[#0b1120]/60 px-4 overflow-x-auto" data-testid="section-bar">
      <div className="flex gap-1 min-w-max">
        {sections.map((s, i) => {
          const done = s.question_ids.filter((q) => isAnswered(answers[q])).length;
          const isActive = sectional ? i === current : i === active;
          const past = sectional && i < current;
          const locked = sectional && i > current;
          return (
            <button key={s.name + i} type="button" disabled={sectional} onClick={() => onSelect?.(i)}
                    data-testid={`section-tab-${i}`}
                    className={`flex items-center gap-2 px-4 py-2.5 text-sm border-b-2 transition-colors whitespace-nowrap
                      ${isActive ? "border-cyan-400 text-white" : "border-transparent text-gray-400"}
                      ${!sectional ? "hover:text-white" : "cursor-default"}`}>
              {past && <Check className="w-3.5 h-3.5 text-emerald-400" />}
              {locked && <Lock className="w-3.5 h-3.5 text-gray-600" />}
              {s.name}
              <span className="mono-font text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-gray-300">
                {sectional && locked ? `${s.duration_minutes}m` : `${done}/${s.question_ids.length}`}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
