import React, { useEffect, useRef, useState } from "react";
import { Play, Pause, SkipBack, SkipForward, RotateCcw, Loader2 } from "lucide-react";
import { useYouTube, youtubeId } from "../lib/youtube";

const fmt = (s) => { s = Math.floor(s || 0); const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = String(s % 60).padStart(2, "0"); return h ? `${h}:${String(m).padStart(2, "0")}:${x}` : `${m}:${x}`; };
const Ctl = ({ onClick, disabled, label, children, testid }) => (
  <button type="button" onClick={onClick} disabled={disabled} aria-label={label} title={label} data-testid={testid}
          className="p-2 rounded-md text-gray-200 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors">{children}</button>
);

function Cover({ img, children, dim }) {
  return (
    <div className="absolute inset-0 z-20 flex items-center justify-center">
      {img && <img src={img} alt="" className="absolute inset-0 w-full h-full object-cover" />}
      <div className={`absolute inset-0 ${dim}`} />
      <div className="relative flex flex-col items-center gap-3">{children}</div>
    </div>
  );
}

const RATES = [0.5, 0.75, 1, 1.25, 1.5, 2];
const RATE_KEY = "player_rate";

export default function LessonPlayer({ url, cover, onPrev, onNext, hasPrev, hasNext, onEnded, resumeAt = 0, onSavePosition }) {
  const vid = youtubeId(url);
  const [rate, setRate] = useState(() => Number(localStorage.getItem(RATE_KEY)) || 1);
  const { host, state, controls } = useYouTube(vid, { onEnded, rate });
  const ctl = useRef(controls);
  ctl.current = controls;
  const saver = useRef(onSavePosition);
  saver.current = onSavePosition;
  const save = () => { const c = ctl.current.current(); if (c.duration) saver.current?.(c.time, c.duration); };

  useEffect(() => {
    if (!state.playing) return undefined;
    const t = setInterval(save, 5000);
    return () => { clearInterval(t); save(); };
  }, [state.playing]);
  useEffect(() => () => save(), []);
  const changeRate = (r) => { setRate(r); localStorage.setItem(RATE_KEY, String(r)); controls.setRate(r); };
  const canResume = resumeAt > 5 && (!state.duration || resumeAt < state.duration * 0.95);
  const resume = () => { controls.play(); controls.seek(resumeAt); };
  if (!vid) {
    return <div className="aspect-video bg-black"><iframe title="Lesson video" src={url} className="w-full h-full" allowFullScreen /></div>;
  }
  const poster = cover || `https://i.ytimg.com/vi/${vid}/hqdefault.jpg`;
  const big = "w-16 h-16 rounded-full bg-blue-600 hover:bg-blue-500 flex items-center justify-center shadow-xl shadow-blue-900/40 transition-transform hover:scale-105";
  return (
    <div data-testid="lesson-player" onContextMenu={(e) => e.preventDefault()}>
      <div className="relative aspect-video bg-black overflow-hidden select-none">
        {/* Oversized frame crops YouTube's title bar & logo strip out of view */}
        <div ref={host} className="absolute left-0 w-full pointer-events-none" style={{ top: "-60px", height: "calc(100% + 120px)" }} />
        <button type="button" onClick={controls.toggle} className="absolute inset-0 z-10 cursor-pointer" aria-label={state.playing ? "Pause" : "Play"} data-testid="player-surface" />
        {!state.started && (
          <Cover img={poster} dim="bg-black/40">
            {canResume && state.ready ? (
              <div className="flex flex-col sm:flex-row gap-3" data-testid="resume-prompt">
                <button type="button" onClick={resume} className="px-5 py-2.5 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium flex items-center gap-2 shadow-xl" data-testid="player-resume-from">
                  <Play className="w-4 h-4" fill="currentColor" />Resume from {fmt(resumeAt)}
                </button>
                <button type="button" onClick={controls.play} className="px-5 py-2.5 rounded-md border border-white/40 bg-black/40 text-white text-sm flex items-center gap-2 hover:bg-white/10" data-testid="player-start-over">
                  <RotateCcw className="w-4 h-4" />Start over
                </button>
              </div>
            ) : (
              <button type="button" onClick={controls.play} disabled={!state.ready} className={big} aria-label="Play" data-testid="player-start">
                {state.ready ? <Play className="w-7 h-7 text-white ml-1" fill="currentColor" /> : <Loader2 className="w-7 h-7 text-white animate-spin" />}
              </button>
            )}
          </Cover>
        )}
        {state.started && !state.playing && !state.ended && (
          <Cover dim="bg-black/85 backdrop-blur-sm">
            <button type="button" onClick={controls.play} className={big} aria-label="Resume" data-testid="player-resume"><Play className="w-7 h-7 text-white ml-1" fill="currentColor" /></button>
            <span className="text-xs text-gray-300 mono-font">PAUSED · {fmt(state.time)}</span>
          </Cover>
        )}
        {state.ended && (
          <Cover img={poster} dim="bg-black/85">
            <div className="flex gap-3">
              <button type="button" onClick={() => controls.seek(0) || controls.play()} className="px-4 py-2 rounded-md border border-white/30 text-white text-sm flex items-center gap-2 hover:bg-white/10" data-testid="player-replay"><RotateCcw className="w-4 h-4" />Replay</button>
              {hasNext && <button type="button" onClick={onNext} className="px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-sm flex items-center gap-2" data-testid="player-ended-next">Next lesson<SkipForward className="w-4 h-4" /></button>}
            </div>
          </Cover>
        )}
      </div>
      <div className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-2 bg-[#0b1120] border-t border-gray-800">
        <Ctl onClick={onPrev} disabled={!hasPrev} label="Previous lesson" testid="player-prev"><SkipBack className="w-5 h-5" /></Ctl>
        <Ctl onClick={controls.toggle} disabled={!state.ready} label={state.playing ? "Pause" : "Play"} testid="player-toggle">
          {state.playing ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
        </Ctl>
        <Ctl onClick={onNext} disabled={!hasNext} label="Next lesson" testid="player-next"><SkipForward className="w-5 h-5" /></Ctl>
        <input type="range" min="0" max={state.duration || 0} step="1" value={Math.min(state.time, state.duration || 0)} disabled={!state.started}
               onChange={(e) => controls.seek(Number(e.target.value))} aria-label="Seek" data-testid="player-seek"
               className="flex-1 mx-2 h-1.5 accent-blue-500 cursor-pointer disabled:cursor-default" />
        <span className="text-xs mono-font text-gray-400 whitespace-nowrap" data-testid="player-time">{fmt(state.time)} / {fmt(state.duration)}</span>
        <select value={rate} onChange={(e) => changeRate(Number(e.target.value))} aria-label="Playback speed" data-testid="player-speed"
                className="ml-1 bg-transparent border border-gray-700 rounded px-1.5 py-1 text-xs mono-font text-gray-200 focus:outline-none focus:border-blue-500 cursor-pointer">
          {RATES.map((r) => <option key={r} value={r} className="bg-[#0b1120]">{r}×</option>)}
        </select>
      </div>
    </div>
  );
}
