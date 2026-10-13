import React from "react";
import { Flag, ChevronLeft, ChevronRight, ChevronsRight } from "lucide-react";
import { Button } from "../../components/ui/button";
import { pick } from "../../components/LangToggle";

const ghost = "border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800";

export default function QuestionPanel({ q, lang, number, total, answer, isMarked, saving, onToggle, onNumeric, onMark, onClear, onPrev, onNext, nextIsSection, isFirst, isLast }) {
  const sel = (key) => (Array.isArray(answer) ? answer.includes(key) : answer === key);
  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div className="text-sm text-gray-400 mono-font" data-testid="question-counter">Question {number} / {total}</div>
        <div className="flex items-center gap-3 text-xs text-gray-400 mono-font">
          <span className="text-emerald-300">+{q.positive_marks}</span>
          <span className="text-rose-300">-{q.negative_marks}</span>
          {q.type === "mcq_multi" && <span className="text-cyan-300">MULTIPLE CORRECT</span>}
          {saving && <span className="text-cyan-300 animate-pulse">Saving…</span>}
        </div>
      </div>
      <div className="card-elev p-5 sm:p-6">
        <div className="text-white text-base sm:text-lg leading-relaxed" data-testid="exam-question-text">{pick(lang, q.text, q.text_hi)}</div>
        {q.image_url && <img src={q.image_url} alt="" className="mt-4 rounded-md max-h-80" />}
        {q.type === "numerical" ? (
          <input type="number" step="any" value={answer ?? ""} onChange={(e) => onNumeric(e.target.value)} placeholder="Enter your answer"
                 className="mt-5 w-full sm:w-64 px-3 py-2 rounded-md bg-[#0b1120] border border-gray-700 text-white mono-font focus:outline-none focus:border-blue-500" data-testid="numeric-answer" />
        ) : (
          <div className="mt-5 space-y-2">
            {q.options?.map((o) => (
              <button key={o.key} onClick={() => onToggle(o.key)} data-testid={`option-${o.key}`}
                      className={`w-full text-left p-3 rounded-md border transition-colors ${sel(o.key) ? "border-blue-500 bg-blue-500/10 text-white" : "border-gray-800 hover:border-gray-600 text-gray-300"}`}>
                <span className="mono-font font-semibold mr-3">{o.key}.</span>{pick(lang, o.text, o.text_hi)}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="mt-5 flex flex-wrap gap-3">
        <Button variant="outline" onClick={onMark} data-testid="mark-review-btn" className="border-violet-500/40 bg-violet-500/10 text-violet-200 hover:bg-violet-500/20">
          <Flag className="w-4 h-4 mr-1" />{isMarked ? "Unmark" : "Mark for Review"}
        </Button>
        <Button variant="outline" onClick={onClear} data-testid="clear-response-btn" className={ghost}>Clear Response</Button>
        <div className="ml-auto flex gap-2">
          <Button onClick={onPrev} disabled={isFirst} variant="outline" className={ghost} data-testid="prev-btn"><ChevronLeft className="w-4 h-4" /> Prev</Button>
          {isLast && nextIsSection ? (
            <Button onClick={onNext} className="bg-violet-600 hover:bg-violet-700" data-testid="next-section-inline-btn">Next section <ChevronsRight className="w-4 h-4" /></Button>
          ) : (
            <Button onClick={onNext} disabled={isLast} className="bg-blue-600 hover:bg-blue-700" data-testid="next-btn">Save & Next <ChevronRight className="w-4 h-4" /></Button>
          )}
        </div>
      </div>
    </div>
  );
}
