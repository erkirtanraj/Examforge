import React from "react";
import { Clock, Send, ChevronsRight } from "lucide-react";
import { Button } from "../../components/ui/button";
import { hms } from "./useCountdown";
import LangToggle from "../../components/LangToggle";

export default function ExamTopBar({ title, timeLeft, sectional, sectionName, isLastSection, onSubmit, showLang, lang, onLang }) {
  const tone = timeLeft < 60 ? "bg-rose-500/10 border-rose-500/40 text-rose-300 animate-pulse"
    : timeLeft < 300 ? "bg-amber-500/10 border-amber-500/40 text-amber-300"
    : "bg-emerald-500/10 border-emerald-500/40 text-emerald-300";
  return (
    <div className="border-b border-gray-800 bg-[#0b1120] px-4 py-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
      <div className="min-w-0 w-full sm:w-auto sm:flex-1">
        <div className="text-xs text-gray-400 mono-font uppercase truncate">{sectional ? `Section · ${sectionName}` : "Attempt in progress"}</div>
        <div className="heading-font text-sm font-semibold truncate" data-testid="exam-title">{title || "Online Examination"}</div>
      </div>
      <div className="flex flex-col items-center">
        <div className={`flex items-center gap-2 px-3 py-1.5 sm:px-4 sm:py-2 rounded-md mono-font text-base sm:text-lg font-bold border ${tone}`} data-testid="exam-timer">
          <Clock className="w-5 h-5" /> {hms(timeLeft)}
        </div>
        {sectional && <div className="text-[10px] mono-font text-gray-500 mt-1 uppercase">Section time left</div>}
      </div>
      <div className="flex items-center gap-2 sm:gap-3">
      {showLang && <LangToggle lang={lang} onChange={onLang} testid="exam-lang" />}
      {sectional && !isLastSection ? (
        <Button onClick={onSubmit} data-testid="exam-next-section-btn" className="bg-violet-600 hover:bg-violet-700">
          <ChevronsRight className="w-4 h-4 mr-1" /><span className="hidden sm:inline">Submit section</span><span className="sm:hidden">End section</span>
        </Button>
      ) : (
        <Button onClick={onSubmit} data-testid="exam-submit-btn" className="bg-rose-600 hover:bg-rose-700">
          <Send className="w-4 h-4 mr-1" /> Submit
        </Button>
      )}
      </div>
    </div>
  );
}
