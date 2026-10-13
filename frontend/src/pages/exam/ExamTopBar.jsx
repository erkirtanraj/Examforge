import React from "react";
import { CheckCircle2, XCircle, Maximize2, Minimize2, Pause, Send, ChevronsRight, UserCircle2 } from "lucide-react";
import { hms } from "./useCountdown";
import LangToggle from "../../components/LangToggle";
import BrandLogo from "../../components/BrandLogo";

const IconBtn = ({ onClick, label, children, testid }) => (
  <button type="button" onClick={onClick} aria-label={label} title={label} data-testid={testid}
          className="w-10 h-10 shrink-0 rounded-lg border border-white/25 bg-white/5 hover:bg-white/15 flex items-center justify-center transition-colors">{children}</button>
);

export default function ExamTopBar({ title, timeLeft, sectional, sectionName, isLastSection, onSubmit, showLang, lang, onLang,
  total, marks, userName, canPause, onPause, fullscreen, onFullscreen }) {
  const timeTone = timeLeft < 60 ? "text-rose-200 animate-pulse" : timeLeft < 300 ? "text-amber-200" : "text-white";
  const endSection = sectional && !isLastSection;
  return (
    <header className="bg-blue-800 text-white shadow-lg shadow-black/30" data-testid="exam-header">
      <div className="max-w-[1600px] mx-auto px-3 sm:px-5 py-2.5 flex flex-wrap items-center gap-x-4 gap-y-2">
        <div className="hidden md:flex items-center gap-2 pr-4 border-r border-white/20 max-w-[200px]"><BrandLogo small /></div>

        <div className="min-w-0 flex-1 basis-[200px]">
          <div className="text-[10px] tracking-[0.2em] text-white/70 mono-font">TEST IN PROGRESS</div>
          <div className="heading-font text-sm sm:text-lg font-bold truncate" data-testid="exam-title" title={title}>{title || "Online Examination"}</div>
          <div className="mt-1 flex flex-wrap gap-1.5 text-[11px]">
            {sectionName && <span className="px-2 py-0.5 rounded-full bg-amber-400 text-black font-semibold truncate max-w-[220px]" data-testid="exam-section-badge">Section: {sectionName}</span>}
            <span className="px-2 py-0.5 rounded-full bg-white/15 border border-white/20">{total} Questions</span>
          </div>
        </div>

        <div className="flex items-center justify-between sm:justify-end gap-3 sm:gap-4 w-full sm:w-auto sm:ml-auto">
          <div className="rounded-lg bg-white text-gray-900 px-3 py-1.5 text-center" data-testid="exam-marking">
            <div className="text-[9px] tracking-[0.15em] text-gray-500 font-semibold">MARKING</div>
            <div className="flex items-center gap-3 text-sm font-bold">
              <span className="flex items-center gap-1 text-emerald-600"><CheckCircle2 className="w-4 h-4" />+{marks.pos}</span>
              <span className="flex items-center gap-1 text-rose-600"><XCircle className="w-4 h-4" />-{marks.neg}</span>
            </div>
          </div>
          <div className="text-center" data-testid="exam-timer">
            <div className={`mono-font text-2xl sm:text-3xl font-bold leading-none ${timeTone}`}>{hms(timeLeft)}</div>
            <div className="text-[9px] tracking-[0.15em] text-white/70 mt-1">{sectional ? "SECTION TIMER" : "TIME LEFT"}</div>
          </div>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          <div className="hidden xl:flex items-center gap-2 px-3 border-l border-white/20" data-testid="exam-user">
            <UserCircle2 className="w-8 h-8 text-white/90" />
            <div className="leading-tight"><div className="text-sm font-semibold truncate max-w-[140px]">{userName}</div><div className="text-[10px] text-white/70">Test Taker</div></div>
          </div>
          {showLang && <LangToggle lang={lang} onChange={onLang} testid="exam-lang" />}
          {canPause && <IconBtn onClick={onPause} label="Pause test" testid="exam-pause-btn"><Pause className="w-4 h-4" /></IconBtn>}
          <IconBtn onClick={onFullscreen} label={fullscreen ? "Exit full screen" : "Full screen"} testid="exam-fullscreen-btn">
            {fullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </IconBtn>
          <button type="button" onClick={onSubmit} data-testid={endSection ? "exam-next-section-btn" : "exam-submit-btn"}
                  className="h-10 px-4 rounded-lg bg-white text-blue-800 font-bold text-sm hover:bg-blue-50 flex items-center gap-1.5 transition-colors whitespace-nowrap">
            {endSection ? <><ChevronsRight className="w-4 h-4" />Submit section</> : <><Send className="w-4 h-4" />Submit test</>}
          </button>
        </div>
      </div>
    </header>
  );
}
