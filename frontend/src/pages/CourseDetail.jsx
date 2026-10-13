import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { CheckCircle2, PlayCircle, FileText } from "lucide-react";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";

export default function CourseDetail() {
  const { id } = useParams();
  const [course, setCourse] = useState(null);
  const [active, setActive] = useState(null);
  const [progress, setProgress] = useState({ completed: 0, total: 0, percent: 0 });
  const [done, setDone] = useState(new Set());
  const { user } = useAuth();

  const loadProgress = async () => {
    if (!user) return;
    const { data } = await api.get(`/my/progress/${id}`);
    setProgress(data);
  };

  useEffect(() => {
    api.get(`/courses/${id}`).then((r) => {
      setCourse(r.data);
      const first = r.data.sections?.[0]?.lessons?.[0];
      setActive(first);
    });
    loadProgress();
    // eslint-disable-next-line
  }, [id]);

  const markDone = async () => {
    if (!active || !user) return;
    await api.post(`/lessons/${active.id}/complete`);
    setDone((d) => new Set(d).add(active.id));
    toast.success("Lesson marked complete");
    loadProgress();
  };

  if (!course) return <div className="max-w-7xl mx-auto p-8 text-gray-400">Loading…</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      <div className="mb-5">
        <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider">Course</div>
        <h1 className="heading-font text-2xl sm:text-3xl font-bold text-white">{course.title}</h1>
        <div className="mt-3 flex items-center gap-3">
          <div className="flex-1 max-w-md h-2 rounded-full bg-gray-800 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-all duration-500" style={{ width: `${progress.percent}%` }} />
          </div>
          <span className="text-xs text-cyan-300 mono-font">{progress.completed}/{progress.total} · {progress.percent}%</span>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="card-elev p-0 overflow-hidden">
            <div className="aspect-video bg-black">
              {active?.content_type === "video" && active?.content_url ? (
                <iframe title={active.title} src={active.content_url} className="w-full h-full" allowFullScreen />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <PlayCircle className="w-16 h-16" />
                </div>
              )}
            </div>
            <div className="p-5">
              <div className="text-xs text-gray-400 mono-font uppercase">Now playing</div>
              <h2 className="heading-font text-lg font-semibold text-white">{active?.title}</h2>
              {active?.text_content && <p className="text-sm text-gray-400 mt-2">{active.text_content}</p>}
              <Button onClick={markDone} className="mt-4 bg-emerald-600 hover:bg-emerald-700" data-testid="mark-lesson-complete">
                <CheckCircle2 className="w-4 h-4 mr-1" /> Mark as complete
              </Button>
            </div>
          </div>
        </div>

        <aside className="space-y-4">
          {course.sections?.map((s) => (
            <div key={s.id} className="card-elev p-4">
              <div className="heading-font text-sm font-semibold text-white mb-2">{s.title}</div>
              <div className="space-y-1">
                {s.lessons?.map((l) => (
                  <button key={l.id} onClick={() => setActive(l)} data-testid={`lesson-${l.id}`}
                          className={`w-full text-left p-2 rounded text-sm flex items-center gap-2 transition-colors
                            ${active?.id === l.id ? "bg-blue-500/10 text-blue-300" : "text-gray-300 hover:bg-gray-800"}`}>
                    {done.has(l.id) ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" /> : <PlayCircle className="w-4 h-4 shrink-0" />}
                    <span className="truncate">{l.title}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </aside>
      </div>
    </div>
  );
}
