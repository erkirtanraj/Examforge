import React from "react";
import { Flag, ChevronLeft, ChevronRight, ChevronsRight, Eraser } from "lucide-react";
import { Button } from "../../components/ui/button";
import { pick } from "../../components/LangToggle";

const ghost = "border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800";

export default function QuestionPanel({ q, lang, number, total, sectionName, sectionMinutes, answer, isMarked, saving, onToggle, onNumeric, onMark, onClear, onPrev, onNext, nextIsSection, isFirst, isLast }) {
  const sel = (key) => (Array.isArray(answer) ? answer.includes(key) : answer === key);
  return (
    <div className="flex flex-col min-h-full rounded-xl border border-gray-800 bg-[#0d1424]" data-testid="question-panel">
      <div className="p-4 sm:p-6 flex-1">
        <div className="flex flex-wrap items-center gap-2 mb-5">
          <span className="px-3 py-1.5 rounded-lg bg-blue-700 text-white text-sm font-semibold" data-testid="question-counter">Question {number} of {total}</span>
          {sectionName && (
            <span className="px-3 py-1.5 rounded-lg border border-blue-500/40 bg-blue-500/10 text-blue-200 text-sm font-medium truncate max-w-full">
              {sectionName}{sectionMinutes ? <span className="ml-2 mono-font text-xs text-blue-300/80">{sectionMinutes} min</span> : null}
            </span>
          )}
          {q.type === "mcq_multi" && <span className="text-[11px] mono-font text-cyan-300 border border-cyan-500/30 rounded px-2 py-1">MULTIPLE CORRECT</span>}
          {saving && <span className="ml-auto text-xs mono-font text-cyan-300 animate-pulse">Saving…</span>}
        </div>
        <div className="text-white text-base sm:text-lg leading-relaxed" data-testid="exam-question-text">{pick(lang, q.text, q.text_hi)}</div>
        {q.image_url && <img loading="lazy" decoding="async" src={q.image_url} alt="" className="mt-4 rounded-md max-h-80" />}
        {q.type === "numerical" ? (
          <input type="number" step="any" value={answer ?? ""} onChange={(e) => onNumeric(e.target.value)} placeholder="Enter your answer"
                 className="mt-5 w-full sm:w-64 px-3 py-2 rounded-md bg-[#0b1120] border border-gray-700 text-white mono-font focus:outline-none focus:border-blue-500" data-testid="numeric-answer" />
        ) : (
          <div className="mt-5 space-y-2.5">
            {q.options?.map((o) => (
              <button key={o.key} onClick={() => onToggle(o.key)} data-testid={`option-${o.key}`}
                      className={`w-full text-left px-4 py-3.5 rounded-lg border transition-colors flex items-start gap-3 ${sel(o.key) ? "border-blue-500 bg-blue-500/15 text-white" : "border-gray-800 hover:border-gray-600 text-gray-200"}`}>
                <span className={`mono-font font-bold shrink-0 ${sel(o.key) ? "text-blue-300" : "text-gray-400"}`}>{o.key}.</span>
                <span>{pick(lang, o.text, o.text_hi)}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="sticky bottom-0 border-t border-gray-800 bg-[#0d1424]/95 backdrop-blur px-3 sm:px-6 py-3 rounded-b-xl flex items-center gap-2 min-w-0">
        <Button variant="outline" onClick={onClear} data-testid="clear-response-btn" className={ghost}><Eraser className="w-4 h-4 sm:mr-1" /><span className="hidden sm:inline">Clear</span></Button>
        <Button variant="outline" onClick={onMark} data-testid="mark-review-btn" className={`${isMarked ? "border-violet-400 bg-violet-500/25" : "border-violet-500/40 bg-violet-500/10"} text-violet-100 hover:bg-violet-500/20`}>
          <Flag className="w-4 h-4 mr-1" />{isMarked ? "Unmark" : <><span className="hidden sm:inline">Mark for review</span><span className="sm:hidden">Review</span></>}
        </Button>
        <div className="ml-auto flex gap-2 shrink-0">
          <Button onClick={onPrev} disabled={isFirst} variant="outline" className={ghost} data-testid="prev-btn"><ChevronLeft className="w-4 h-4" /><span className="hidden sm:inline">Prev</span></Button>
          {isLast && nextIsSection ? (
            <Button onClick={onNext} className="bg-violet-600 hover:bg-violet-700" data-testid="next-section-inline-btn"><span className="hidden sm:inline">Next section</span><span className="sm:hidden">Section</span><ChevronsRight className="w-4 h-4" /></Button>
          ) : (
            <Button onClick={onNext} disabled={isLast} className="bg-blue-700 hover:bg-blue-600 font-semibold" data-testid="next-btn"><span className="hidden sm:inline">Save & Next</span><span className="sm:hidden">Next</span><ChevronRight className="w-4 h-4" /></Button>
          )}
        </div>
      </div>
    </div>
  );
}
