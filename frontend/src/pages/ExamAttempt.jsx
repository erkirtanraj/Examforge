import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { Bookmark, Clock, Flag, ChevronLeft, ChevronRight, Send, X } from "lucide-react";
import { toast } from "sonner";

export default function ExamAttempt() {
  const { attemptId } = useParams();
  const [attempt, setAttempt] = useState(null);
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState({});
  const [visited, setVisited] = useState(new Set());
  const [marked, setMarked] = useState(new Set());
  const [timeLeft, setTimeLeft] = useState(0);
  const [submitOpen, setSubmitOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const versionRef = useRef(0);
  const nav = useNavigate();

  useEffect(() => {
    api.get(`/attempts/${attemptId}`).then((r) => {
      setAttempt(r.data);
      setAnswers(r.data.answers || {});
      setMarked(new Set(r.data.marked_for_review || []));
      versionRef.current = r.data.version || 0;
    }).catch((e) => {
      toast.error("Could not load attempt");
      nav("/dashboard");
    });
  }, [attemptId, nav]);

  // Timer
  useEffect(() => {
    if (!attempt) return;
    const end = new Date(attempt.ends_at).getTime();
    const tick = () => {
      const s = Math.max(0, Math.floor((end - Date.now()) / 1000));
      setTimeLeft(s);
      if (s === 0) finalize(true);
    };
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt]);

  // Autosave every 15s
  const autosave = useCallback(async () => {
    if (!attempt || saving) return;
    setSaving(true);
    try {
      const { data } = await api.post(`/attempts/${attemptId}/autosave`, {
        answers,
        marked_for_review: Array.from(marked),
        client_version: versionRef.current,
      });
      if (data.version) versionRef.current = data.version;
      if (data.status === "auto_submitted") {
        toast.info("Time up — attempt submitted");
        nav(`/result/${attemptId}`);
      }
    } catch (_) {}
    finally { setSaving(false); }
  }, [attempt, answers, marked, saving, attemptId, nav]);

  useEffect(() => {
    const i = setInterval(autosave, 15000);
    return () => clearInterval(i);
  }, [autosave]);

  // Mark current as visited
  useEffect(() => {
    if (!attempt?.questions?.[idx]) return;
    setVisited((v) => new Set(v).add(attempt.questions[idx].id));
  }, [idx, attempt]);

  if (!attempt) return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading exam…</div>;
  const q = attempt.questions?.[idx];
  if (!q) return <div className="text-gray-400 p-8">No questions.</div>;

  const setAnswer = (val) => {
    setAnswers((a) => ({ ...a, [q.id]: val }));
  };

  const toggleOption = (key) => {
    if (q.type === "mcq_multi") {
      const cur = Array.isArray(answers[q.id]) ? answers[q.id] : [];
      setAnswer(cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key]);
    } else {
      setAnswer([key]);
    }
  };

  const toggleMark = () => {
    setMarked((m) => {
      const n = new Set(m);
      if (n.has(q.id)) n.delete(q.id); else n.add(q.id);
      return n;
    });
  };

  const clearResp = () => {
    setAnswers((a) => { const n = { ...a }; delete n[q.id]; return n; });
  };

  const statusOf = (qq) => {
    const ans = answers[qq.id];
    const hasAns = Array.isArray(ans) ? ans.length > 0 : ans !== undefined && ans !== "";
    const isMarked = marked.has(qq.id);
    if (hasAns && isMarked) return "qp-ans-marked";
    if (isMarked) return "qp-marked";
    if (hasAns) return "qp-answered";
    if (visited.has(qq.id)) return "qp-not-answered";
    return "qp-not-visited";
  };

  const finalize = async (auto = false) => {
    try {
      const { data } = await api.post(`/attempts/${attemptId}/submit`, {
        answers,
        marked_for_review: Array.from(marked),
      });
      toast.success(auto ? "Auto-submitted" : "Submitted");
      nav(`/result/${attemptId}`);
    } catch (e) {
      toast.error("Submission failed");
    }
  };

  const mmss = (s) => {
    const h = String(Math.floor(s / 3600)).padStart(2, "0");
    const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
    const sec = String(s % 60).padStart(2, "0");
    return `${h}:${m}:${sec}`;
  };

  const warn = timeLeft < 300;
  const danger = timeLeft < 60;

  const stats = {
    answered: attempt.questions.filter((qq) => {
      const a = answers[qq.id]; return Array.isArray(a) ? a.length > 0 : a !== undefined && a !== "";
    }).length,
    marked: marked.size,
    notVisited: attempt.questions.filter((qq) => !visited.has(qq.id)).length,
  };

  return (
    <div className="min-h-screen bg-[#090D16] text-white flex flex-col">
      {/* Top bar */}
      <div className="border-b border-gray-800 bg-[#0b1120] px-4 py-3 flex items-center justify-between">
        <div>
          <div className="text-xs text-gray-400 mono-font uppercase">Attempt in progress</div>
          <div className="heading-font text-sm font-semibold">Online Examination</div>
        </div>
        <div className={`flex items-center gap-2 px-4 py-2 rounded-md mono-font text-lg font-bold border
          ${danger ? "bg-rose-500/10 border-rose-500/40 text-rose-300 animate-pulse" :
            warn ? "bg-amber-500/10 border-amber-500/40 text-amber-300" : "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"}`}
          data-testid="exam-timer">
          <Clock className="w-5 h-5" /> {mmss(timeLeft)}
        </div>
        <Button onClick={() => setSubmitOpen(true)} data-testid="exam-submit-btn" className="bg-rose-600 hover:bg-rose-700">
          <Send className="w-4 h-4 mr-1" /> Submit
        </Button>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row">
        {/* Question area */}
        <div className="flex-1 p-4 sm:p-6 overflow-auto">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center justify-between mb-5">
              <div className="text-sm text-gray-400 mono-font">Question {idx + 1} / {attempt.questions.length}</div>
              <div className="flex items-center gap-3 text-xs text-gray-400 mono-font">
                <span className="text-emerald-300">+{q.positive_marks}</span>
                <span className="text-rose-300">-{q.negative_marks}</span>
                {saving && <span className="text-cyan-300 animate-pulse">Saving…</span>}
              </div>
            </div>
            <div className="card-elev p-5 sm:p-6">
              <div className="text-white text-base sm:text-lg leading-relaxed" data-testid="exam-question-text">{q.text}</div>
              {q.image_url && <img src={q.image_url} alt="" className="mt-4 rounded-md max-h-80" />}
              <div className="mt-5 space-y-2">
                {q.options?.map((o) => {
                  const sel = Array.isArray(answers[q.id]) ? answers[q.id].includes(o.key) : answers[q.id] === o.key;
                  return (
                    <button key={o.key} onClick={() => toggleOption(o.key)} data-testid={`option-${o.key}`}
                            className={`w-full text-left p-3 rounded-md border transition-colors
                              ${sel ? "border-blue-500 bg-blue-500/10 text-white" : "border-gray-800 hover:border-gray-600 text-gray-300"}`}>
                      <span className="mono-font font-semibold mr-3">{o.key}.</span>{o.text}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <Button variant="outline" onClick={toggleMark} data-testid="mark-review-btn"
                      className="border-violet-500/40 bg-violet-500/10 text-violet-200 hover:bg-violet-500/20">
                <Flag className="w-4 h-4 mr-1" />
                {marked.has(q.id) ? "Unmark" : "Mark for Review"}
              </Button>
              <Button variant="outline" onClick={clearResp} data-testid="clear-response-btn"
                      className="border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800">
                Clear Response
              </Button>
              <div className="ml-auto flex gap-2">
                <Button onClick={() => setIdx(Math.max(0, idx - 1))} disabled={idx === 0} variant="outline"
                        className="border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800" data-testid="prev-btn">
                  <ChevronLeft className="w-4 h-4" /> Prev
                </Button>
                <Button onClick={() => { autosave(); setIdx(Math.min(attempt.questions.length - 1, idx + 1)); }}
                        disabled={idx === attempt.questions.length - 1} className="bg-blue-600 hover:bg-blue-700" data-testid="next-btn">
                  Save & Next <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
            <button onClick={() => setPaletteOpen(true)} className="lg:hidden mt-4 w-full py-2 border border-gray-800 rounded-md text-sm text-gray-300">
              Open Question Palette
            </button>
          </div>
        </div>

        {/* Palette */}
        <aside className={`${paletteOpen ? "fixed inset-0 z-50 bg-[#0b1120] overflow-auto" : "hidden"} lg:static lg:block lg:w-80 border-l border-gray-800 bg-[#0b1120]`}>
          <div className="p-4">
            {paletteOpen && <button onClick={() => setPaletteOpen(false)} className="lg:hidden mb-3 text-gray-400"><X /></button>}
            <div className="text-sm text-gray-400 mono-font uppercase mb-1">Progress</div>
            <div className="grid grid-cols-3 gap-2 mb-4 text-center">
              <div className="rounded-md bg-emerald-500/10 border border-emerald-500/30 p-2">
                <div className="text-xl font-bold text-emerald-300" data-testid="stat-answered">{stats.answered}</div>
                <div className="text-[10px] text-gray-400 mono-font">ANSWERED</div>
              </div>
              <div className="rounded-md bg-violet-500/10 border border-violet-500/30 p-2">
                <div className="text-xl font-bold text-violet-300">{stats.marked}</div>
                <div className="text-[10px] text-gray-400 mono-font">MARKED</div>
              </div>
              <div className="rounded-md bg-gray-700/30 border border-gray-700 p-2">
                <div className="text-xl font-bold text-gray-300">{stats.notVisited}</div>
                <div className="text-[10px] text-gray-400 mono-font">LEFT</div>
              </div>
            </div>
            <div className="text-sm text-gray-400 mono-font uppercase mb-2">Question Palette</div>
            <div className="grid grid-cols-5 gap-2" data-testid="question-palette">
              {attempt.questions.map((qq, i) => (
                <button key={qq.id} onClick={() => { setIdx(i); setPaletteOpen(false); }} data-testid={`palette-q-${i + 1}`}
                        className={`${statusOf(qq)} ${i === idx ? "qp-current" : ""} w-full aspect-square rounded mono-font font-semibold text-sm`}>
                  {i + 1}
                </button>
              ))}
            </div>
            <div className="mt-4 text-[11px] mono-font space-y-1.5">
              <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-sm qp-answered inline-block"/><span className="text-gray-400">Answered</span></div>
              <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-sm qp-not-answered inline-block"/><span className="text-gray-400">Not Answered</span></div>
              <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-sm qp-marked inline-block"/><span className="text-gray-400">Marked for Review</span></div>
              <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-sm qp-ans-marked inline-block"/><span className="text-gray-400">Answered & Marked</span></div>
              <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-sm qp-not-visited inline-block"/><span className="text-gray-400">Not Visited</span></div>
            </div>
          </div>
        </aside>
      </div>

      <Dialog open={submitOpen} onOpenChange={setSubmitOpen}>
        <DialogContent className="bg-[#0b1120] border-gray-800 text-white">
          <DialogHeader>
            <DialogTitle className="heading-font">Submit the test?</DialogTitle>
          </DialogHeader>
          <div className="text-sm text-gray-300 space-y-2">
            <div className="grid grid-cols-3 gap-3 my-3">
              <div className="p-3 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-center">
                <div className="text-2xl font-bold text-emerald-300">{stats.answered}</div>
                <div className="text-[10px] mono-font text-gray-400">ANSWERED</div>
              </div>
              <div className="p-3 rounded-md bg-violet-500/10 border border-violet-500/30 text-center">
                <div className="text-2xl font-bold text-violet-300">{stats.marked}</div>
                <div className="text-[10px] mono-font text-gray-400">MARKED</div>
              </div>
              <div className="p-3 rounded-md bg-gray-700/30 border border-gray-700 text-center">
                <div className="text-2xl font-bold text-gray-300">{stats.notVisited}</div>
                <div className="text-[10px] mono-font text-gray-400">UNVISITED</div>
              </div>
            </div>
            <p>Once submitted you can't change your responses. Review your palette first.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSubmitOpen(false)} className="border-gray-700 bg-transparent text-gray-200">Review again</Button>
            <Button onClick={() => finalize(false)} data-testid="exam-confirm-submit" className="bg-rose-600 hover:bg-rose-700">Submit now</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
