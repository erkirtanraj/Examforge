import React from "react";
import { Pause, Play, Loader2 } from "lucide-react";
import { hms } from "./useCountdown";

export default function PauseOverlay({ remaining, pauseLeft, onResume, busy }) {
  return (
    <div className="fixed inset-0 z-[60] bg-[#05070c]/95 backdrop-blur-md flex items-center justify-center p-6" data-testid="pause-overlay">
      <div className="max-w-sm w-full text-center card-elev p-8">
        <div className="mx-auto w-14 h-14 rounded-full bg-blue-600/20 border border-blue-500/40 flex items-center justify-center mb-4"><Pause className="w-6 h-6 text-blue-300" /></div>
        <h2 className="heading-font text-2xl font-bold text-white">Test paused</h2>
        <p className="text-sm text-gray-400 mt-2">Questions are hidden and your exam timer is stopped.</p>
        <div className="mt-5 grid grid-cols-2 gap-3 text-left">
          <div className="rounded-md border border-gray-800 p-3"><div className="text-[10px] text-gray-500 mono-font">EXAM TIME LEFT</div><div className="mono-font text-lg text-white" data-testid="pause-remaining">{hms(remaining)}</div></div>
          <div className="rounded-md border border-gray-800 p-3"><div className="text-[10px] text-gray-500 mono-font">PAUSE LEFT</div><div className={`mono-font text-lg ${pauseLeft < 60 ? "text-rose-300" : "text-amber-300"}`} data-testid="pause-left">{hms(pauseLeft)}</div></div>
        </div>
        <p className="text-[11px] text-gray-500 mt-3">After the pause allowance runs out, the exam timer starts again.</p>
        <button type="button" onClick={onResume} disabled={busy} className="mt-6 w-full h-11 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold flex items-center justify-center gap-2 disabled:opacity-60" data-testid="resume-test-btn">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Play className="w-4 h-4" fill="currentColor" />Resume test</>}
        </button>
      </div>
    </div>
  );
}
