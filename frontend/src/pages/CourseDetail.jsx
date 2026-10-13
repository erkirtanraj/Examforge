import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { CheckCircle2, PlayCircle, FileText, ChevronLeft, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { api, assetUrl } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Button } from "../components/ui/button";
import LessonPlayer from "../components/LessonPlayer";
import CertificateCard from "../components/CertificateCard";

function LessonList({ sections, active, done, onPick, numberOf }) {
  return (
    <aside className="space-y-4" data-testid="lesson-list">
      {sections.map((s) => (
        <div key={s.id} className="card-elev p-4">
          <div className="heading-font text-sm font-semibold text-white mb-2">{s.title}</div>
          <div className="space-y-1">
            {s.lessons?.map((l) => (
              <button key={l.id} onClick={() => onPick(l)} data-testid={`lesson-${l.id}`}
                      className={`w-full text-left p-2 rounded text-sm flex items-center gap-2.5 transition-colors ${active?.id === l.id ? "bg-blue-500/10 text-blue-300" : "text-gray-300 hover:bg-gray-800"}`}>
                <span className="mono-font text-[11px] text-gray-500 w-5 text-right shrink-0">{numberOf[l.id]}</span>
                {done.has(l.id) ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" data-testid={`lesson-done-${l.id}`} />
                  : l.content_type === "video" ? <PlayCircle className="w-4 h-4 shrink-0" /> : <FileText className="w-4 h-4 shrink-0" />}
                <span className="truncate">{l.title}</span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </aside>
  );
}

export default function CourseDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [course, setCourse] = useState(null);
  const [active, setActive] = useState(null);
  const [progress, setProgress] = useState({ completed: 0, total: 0, percent: 0 });
  const [done, setDone] = useState(new Set());
  const [positions, setPositions] = useState({});
  const [cert, setCert] = useState(null);

  const loadProgress = async () => {
    if (!user) return;
    const { data } = await api.get(`/my/progress/${id}`);
    setProgress(data);
    setDone(new Set(data.completed_ids || []));
    setPositions(data.positions || {});
    setCert(data.certificate || null);
  };

  useEffect(() => {
    let cancelled = false;
    api.get(`/courses/${id}`).then((r) => {
      if (cancelled) return;
      setCourse(r.data);
      setActive(r.data.sections?.[0]?.lessons?.[0] || null);
      if (user && !r.data.access_required) loadProgress();
    });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, user]);

  const flat = useMemo(() => (course?.sections || []).flatMap((s) => s.lessons || []), [course]);
  const numberOf = useMemo(() => Object.fromEntries(flat.map((l, i) => [l.id, i + 1])), [flat]);
  const idx = active ? flat.findIndex((l) => l.id === active.id) : -1;
  const pick = (l) => { setActive(l); window.scrollTo({ top: 0, behavior: "smooth" }); };

  const complete = async (quiet = false) => {
    if (!active || !user || done.has(active.id)) return;
    await api.post(`/lessons/${active.id}/complete`);
    if (!quiet) toast.success("Lesson marked complete");
    loadProgress();
  };
  // Navigation alone must not complete a lesson; completion remains explicit or occurs at video end.
  const next = () => { if (idx < flat.length - 1) pick(flat[idx + 1]); };
  const savePosition = (lessonId) => (time, duration) => {
    localStorage.setItem(`lesson_pos_${lessonId}`, JSON.stringify({ time, duration }));
    setPositions((p) => ({ ...p, [lessonId]: { position: time, duration } }));
    if (user) api.put(`/lessons/${lessonId}/position`, { position: time, duration }).catch(() => {});
  };
  const resumeFor = (lessonId) => {
    if (positions[lessonId]) return positions[lessonId].position;
    try { return JSON.parse(localStorage.getItem(`lesson_pos_${lessonId}`))?.time || 0; } catch { return 0; }
  };
  const prev = () => idx > 0 && pick(flat[idx - 1]);

  if (!course) return <div className="max-w-7xl mx-auto p-8 text-gray-400">Loading…</div>;
  if (course.access_required) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
        <div className="card-elev p-6 sm:p-8">
          <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider">Premium course</div>
          <h1 className="heading-font text-2xl sm:text-3xl font-bold text-white mt-2">{course.title}</h1>
          <p className="text-gray-400 mt-3">{course.description}</p>
          <p className="text-sm text-amber-200 mt-5">Enrollment is required to access lesson videos, notes, and progress tracking.</p>
          <a href="/courses" className="inline-flex mt-5 px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-sm">Browse courses</a>
        </div>
      </div>
    );
  }
  const isVideo = active?.content_type === "video" && active?.content_url;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      <div className="mb-5">
        <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider">Course</div>
        <h1 className="heading-font text-2xl sm:text-3xl font-bold text-white">{course.title}</h1>
        {user && (
          <div className="mt-3 flex items-center gap-3">
            <div className="flex-1 max-w-md h-2 rounded-full bg-gray-800 overflow-hidden">
              <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-[width] duration-500" style={{ width: `${progress.percent}%` }} />
            </div>
            <span className="text-xs text-cyan-300 mono-font" data-testid="course-progress">{progress.completed}/{progress.total} · {progress.percent}%</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 min-w-0">
          <div className="card-elev p-0 overflow-hidden">
            {isVideo ? (
              <LessonPlayer key={active.id} url={active.content_url} cover={assetUrl(course.thumbnail)} hasPrev={idx > 0} hasNext={idx < flat.length - 1}
                            onPrev={prev} onNext={next} onEnded={() => complete(true)}
                            resumeAt={resumeFor(active.id)} onSavePosition={savePosition(active.id)} />
            ) : (
              <div className="aspect-video bg-black flex items-center justify-center text-gray-500"><FileText className="w-16 h-16" /></div>
            )}
            <div className="p-5">
              <div className="text-xs text-gray-400 mono-font uppercase" data-testid="lesson-position">Lesson {idx + 1} of {flat.length}</div>
              <h2 className="heading-font text-lg font-semibold text-white" data-testid="active-lesson-title">{active?.title}</h2>
              {active?.text_content && <p className="text-sm text-gray-400 mt-2 whitespace-pre-line">{active.text_content}</p>}
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {user && (done.has(active?.id) ? (
                  <span className="inline-flex items-center gap-1.5 text-sm text-emerald-300" data-testid="lesson-completed-badge"><CheckCircle2 className="w-4 h-4" />Completed</span>
                ) : (
                  <Button onClick={() => complete()} className="bg-emerald-600 hover:bg-emerald-700" data-testid="mark-lesson-complete"><CheckCircle2 className="w-4 h-4 mr-1" />Mark as complete</Button>
                ))}
                <div className="flex gap-2 ml-auto">
                  <Button variant="outline" onClick={prev} disabled={idx <= 0} className="border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800" data-testid="lesson-prev"><ChevronLeft className="w-4 h-4 mr-1" />Previous</Button>
                  <Button onClick={next} disabled={idx >= flat.length - 1} className="bg-blue-600 hover:bg-blue-700" data-testid="lesson-next">Next<ChevronRight className="w-4 h-4 ml-1" /></Button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="space-y-4">
          {course.certificate_enabled && user && <CertificateCard course={course} progress={progress} cert={cert} onIssued={setCert} user={user} />}
          <LessonList sections={course.sections || []} active={active} done={done} onPick={pick} numberOf={numberOf} />
        </div>
      </div>
    </div>
  );
}
