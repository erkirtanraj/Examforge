import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { api } from "../../lib/api";
import { useCountdown, isAnswered } from "./useCountdown";
import ExamTopBar from "./ExamTopBar";
import SectionBar from "./SectionBar";
import QuestionPanel from "./QuestionPanel";
import Palette from "./Palette";
import ConfirmDialog from "./ConfirmDialog";
import PauseOverlay from "./PauseOverlay";
import { LayoutGrid } from "lucide-react";

export default function ExamPage() {
  const { attemptId } = useParams();
  const nav = useNavigate();
  const [attempt, setAttempt] = useState(null);
  const [idx, setIdx] = useState(0);
  const [answers, setAnswers] = useState({});
  const [marked, setMarked] = useState(new Set());
  const [visited, setVisited] = useState(new Set());
  const [dialog, setDialog] = useState(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pausing, setPausing] = useState(false);
  const [fullscreen, setFullscreen] = useState(!!document.fullscreenElement);
  const [lang, setLangState] = useState(() => localStorage.getItem("exam_lang") || "en");
  const setLang = (l) => { setLangState(l); localStorage.setItem("exam_lang", l); };
  const version = useRef(0);
  const live = useRef({ answers: {}, marked: new Set() });
  const busy = useRef(false);

  const toResult = useCallback(() => nav(`/result/${attemptId}`, { replace: true }), [nav, attemptId]);

  const load = useCallback(async () => {
    const { data } = await api.get(`/attempts/${attemptId}`);
    if (data.status !== "in_progress") return toResult();
    setAttempt(data);
    setAnswers(data.answers || {});
    setMarked(new Set(data.marked_for_review || []));
    version.current = data.version || 0;
    setIdx(0);
    busy.current = false;
  }, [attemptId, toResult]);

  useEffect(() => { load().catch(() => { toast.error("Could not load attempt"); nav("/dashboard"); }); }, [load, nav]);
  useEffect(() => { live.current = { answers, marked }; }, [answers, marked]);
  useEffect(() => { const q = attempt?.questions?.[idx]; if (q) setVisited((v) => new Set(v).add(q.id)); }, [idx, attempt]);

  const payload = () => ({ answers: live.current.answers, marked_for_review: Array.from(live.current.marked), client_version: version.current });
  const sectional = !!attempt?.sectional_timing;
  const sections = useMemo(() => attempt?.sections || [], [attempt]);
  const isLastSection = !sectional || attempt.current_section >= sections.length - 1;

  const handleStatus = useCallback((status) => {
    if (status === "auto_submitted" || status === "submitted") { toast.info("Time up — test submitted"); toResult(); return true; }
    if (status === "section_advanced") { toast.info("Section time over — next section started"); load(); return true; }
    return false;
  }, [toResult, load]);

  const save = useCallback(async () => {
    if (busy.current) return;
    setSaving(true);
    try {
      const { data } = await api.post(`/attempts/${attemptId}/autosave`, payload());
      if (data.version) version.current = data.version;
      handleStatus(data.status);
    } catch (_) { /* retried on next tick */ } finally { setSaving(false); }
  }, [attemptId, handleStatus]);

  const paused = !!attempt?.paused_at;
  useEffect(() => { if (!attempt || paused) return; const t = setInterval(save, 15000); return () => clearInterval(t); }, [attempt, paused, save]);
  useEffect(() => {
    const h = () => setFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", h);
    return () => document.removeEventListener("fullscreenchange", h);
  }, []);
  const toggleFullscreen = () => (document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen?.())?.catch?.(() => toast.error("Full screen isn't available in this browser"));

  const pauseTest = async () => {
    if (busy.current) return;
    setPausing(true);
    try {
      const { data } = await api.post(`/attempts/${attemptId}/pause`, payload());
      if (data.status === "submitted") return toResult();
      await load();
    } catch (e) { toast.error(e.response?.data?.detail || "Could not pause"); } finally { setPausing(false); }
  };
  const resumeTest = useCallback(async () => {
    setPausing(true);
    try {
      const { data } = await api.post(`/attempts/${attemptId}/resume`);
      if (data.status === "submitted") { toast.info("Time up — test submitted"); return toResult(); }
      await load();
    } catch { toast.error("Could not resume — please try again"); } finally { setPausing(false); }
  }, [attemptId, load, toResult]);

  const submitTest = async (auto) => {
    if (busy.current) return;
    busy.current = true;
    try { await api.post(`/attempts/${attemptId}/submit`, payload()); toast.success(auto ? "Time up — test submitted" : "Test submitted"); toResult(); }
    catch { busy.current = false; toast.error("Submission failed — please try again"); }
  };
  const nextSection = async (auto) => {
    if (busy.current) return;
    busy.current = true;
    setDialog(null);
    try {
      const { data } = await api.post(`/attempts/${attemptId}/next-section`, payload());
      if (data.status === "submitted") return toResult();
      toast.info(auto ? "Section time over — next section started" : "Next section started");
      await load();
    } catch { busy.current = false; toast.error("Could not start the next section"); }
  };

  const deadline = attempt && !paused ? (sectional ? attempt.section_ends_at : attempt.ends_at) : null;
  const pauseDeadline = paused ? new Date(new Date(attempt.paused_at).getTime() + (attempt.pause_left_seconds || 0) * 1000).toISOString() : null;
  const pauseLeft = useCountdown(pauseDeadline, resumeTest);
  const timeLeft = useCountdown(deadline, () => (sectional && !isLastSection ? nextSection(true) : submitTest(true)));

  const sectionOf = useMemo(() => {
    const m = {};
    sections.forEach((s, i) => s.question_ids.forEach((q) => { m[q] = i; }));
    return m;
  }, [sections]);

  if (!attempt) return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading exam…</div>;
  const qs = attempt.questions || [];
  const q = qs[idx];
  if (!q) return <div className="text-gray-400 p-8">No questions.</div>;

  const activeSection = sectional ? attempt.current_section : sectionOf[q.id] ?? 0;
  const multi = !sectional && sections.length > 1;
  const indexed = qs.map((qq, i) => ({ q: qq, i }));
  const groups = multi
    ? sections.map((s, si) => ({ name: s.name, minutes: s.duration_minutes, items: indexed.filter(({ q: qq }) => sectionOf[qq.id] === si) })).filter((g) => g.items.length)
    : [{ name: sections[activeSection]?.name || "", minutes: sections[activeSection]?.duration_minutes, items: indexed }];
  const statusOf = (qq) => {
    const a = isAnswered(answers[qq.id]); const m = marked.has(qq.id);
    return a && m ? "qp-ans-marked" : m ? "qp-marked" : a ? "qp-answered" : visited.has(qq.id) ? "qp-not-answered" : "qp-not-visited";
  };
  const scope = qs;
  const stats = {
    answered: scope.filter((x) => isAnswered(answers[x.id])).length,
    notAnswered: scope.filter((x) => visited.has(x.id) && !isAnswered(answers[x.id])).length,
    marked: scope.filter((x) => marked.has(x.id)).length,
    notVisited: scope.filter((x) => !visited.has(x.id)).length,
  };
  const setAns = (v) => setAnswers((a) => ({ ...a, [q.id]: v }));
  const toggle = (key) => {
    if (q.type !== "mcq_multi") return setAns([key]);
    const cur = Array.isArray(answers[q.id]) ? answers[q.id] : [];
    setAns(cur.includes(key) ? cur.filter((k) => k !== key) : [...cur, key]);
  };
  const sectionName = sections[activeSection]?.name;
  const remainingPaused = Math.max(0, Math.floor(sectional ? attempt.section_remaining_at_pause || 0 : attempt.remaining_at_pause || 0));

  return (
    <div className="min-h-screen bg-[#070a12] text-white flex flex-col">
      <ExamTopBar title={attempt.test_title} timeLeft={paused ? remainingPaused : timeLeft} showLang={qs.some((x) => x.text_hi)} lang={lang} onLang={setLang}
                  sectional={sectional} sectionName={sectionName} isLastSection={isLastSection} total={qs.length}
                  marks={{ pos: q.positive_marks, neg: q.negative_marks }} userName={attempt.user_name}
                  canPause={(attempt.pause_left_seconds || 0) > 0} onPause={pauseTest} fullscreen={fullscreen} onFullscreen={toggleFullscreen}
                  onSubmit={() => setDialog(sectional && !isLastSection ? "section" : "submit")} />
      <SectionBar sections={sections} sectional={sectional} current={attempt.current_section} active={activeSection}
                  answers={answers} onSelect={(i) => setIdx(qs.findIndex((x) => sectionOf[x.id] === i))} />
      <div className="flex-1 w-full max-w-[1600px] mx-auto p-3 sm:p-5 flex flex-col lg:flex-row gap-4 lg:gap-5 lg:items-start">
        <div className="flex-1 min-w-0 flex flex-col gap-3">
          <button onClick={() => setPaletteOpen(true)} data-testid="open-palette-btn"
                  className="lg:hidden w-full py-2.5 px-4 border border-gray-800 rounded-lg text-sm text-gray-200 bg-[#0b1120] flex items-center justify-between">
            <span className="flex items-center gap-2"><LayoutGrid className="w-4 h-4" />Question palette</span>
            <span className="mono-font text-xs text-gray-400">{stats.answered}/{qs.length} answered</span>
          </button>
          <QuestionPanel q={q} lang={lang} number={idx + 1} total={qs.length} sectionName={sectionName} sectionMinutes={sections[activeSection]?.duration_minutes}
            answer={answers[q.id]} isMarked={marked.has(q.id)} saving={saving}
            onToggle={toggle} onNumeric={setAns}
            onMark={() => setMarked((m) => { const n = new Set(m); n.has(q.id) ? n.delete(q.id) : n.add(q.id); return n; })}
            onClear={() => setAnswers((a) => { const n = { ...a }; delete n[q.id]; return n; })}
            onPrev={() => setIdx(Math.max(0, idx - 1))} isFirst={idx === 0} isLast={idx === qs.length - 1}
            nextIsSection={sectional && !isLastSection}
            onNext={() => (idx === qs.length - 1 ? setDialog("section") : (save(), setIdx(idx + 1)))} />
        </div>
        <Palette groups={groups} idx={idx} statusOf={statusOf} stats={stats} open={paletteOpen}
                 onClose={() => setPaletteOpen(false)} onJump={(i) => { setIdx(i); setPaletteOpen(false); }} />
      </div>
      {paused && <PauseOverlay remaining={remainingPaused} pauseLeft={pauseLeft} onResume={resumeTest} busy={pausing} />}
      <ConfirmDialog kind={dialog} onClose={() => setDialog(null)} stats={stats} sectionName={sectionName}
                     nextSectionName={sections[activeSection + 1]?.name}
                     onConfirm={() => (dialog === "section" ? nextSection(false) : submitTest(false))} />
    </div>
  );
}
