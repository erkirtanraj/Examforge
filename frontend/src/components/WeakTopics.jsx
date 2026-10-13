import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { TrendingDown, TrendingUp, Target, ArrowRight, Lock } from "lucide-react";
import { api } from "../lib/api";

const LEVEL = {
  weak: ["text-rose-300 border-rose-500/40 bg-rose-500/10", "from-rose-500 to-orange-400", "WEAK"],
  average: ["text-amber-300 border-amber-500/40 bg-amber-500/10", "from-amber-500 to-yellow-400", "AVERAGE"],
  strong: ["text-emerald-300 border-emerald-500/40 bg-emerald-500/10", "from-emerald-500 to-cyan-400", "STRONG"],
};

const Trend = ({ v }) => {
  if (v == null) return <span className="text-gray-600">—</span>;
  const up = v >= 0;
  const Icon = up ? TrendingUp : TrendingDown;
  return <span className={`flex items-center gap-1 ${up ? "text-emerald-300" : "text-rose-300"}`}><Icon className="w-3.5 h-3.5" />{up ? "+" : ""}{v}%</span>;
};

const TopicRow = ({ t }) => {
  const [pill, bar, label] = LEVEL[t.level];
  return (
    <div className="card-elev p-4" data-testid={`weak-topic-${t.name.toLowerCase().replace(/\s+/g, "-")}`}>
      <div className="flex flex-wrap items-center gap-3">
        <div className="heading-font font-semibold text-white flex-1 min-w-[160px]">{t.name}</div>
        <span className={`text-[10px] mono-font px-2 py-0.5 rounded border ${pill}`}>{label}</span>
        <div className="flex items-center gap-4 text-xs mono-font text-gray-400">
          <span>ACC {t.accuracy}%</span><span>{t.attempts} MOCK{t.attempts === 1 ? "" : "S"}</span><Trend v={t.trend} />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <div className="flex-1 h-2 rounded-full bg-gray-800 overflow-hidden"><div className={`h-full bg-gradient-to-r ${bar} transition-[width] duration-700`} style={{ width: `${t.score_pct}%` }} /></div>
        <span className="mono-font text-sm text-white w-14 text-right">{t.score_pct}%</span>
      </div>
      {t.suggestions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="text-[10px] mono-font text-gray-500 uppercase self-center">Practice</span>
          {t.suggestions.map((s) => (
            <Link key={s.test_id} to={`/test-series/${s.series_id}`} data-testid={`suggestion-${s.test_id}`}
                  className="text-xs px-2.5 py-1 rounded-md border border-gray-700 text-gray-200 hover:border-blue-500/60 hover:text-white transition-colors flex items-center gap-1">
              {!s.has_access && <Lock className="w-3 h-3 text-amber-300" />}{s.title}{s.attempted && <span className="text-gray-500">· retake</span>}<ArrowRight className="w-3 h-3" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};

const SubjectRow = ({ t }) => {
  const [pill, bar, label] = LEVEL[t.level];
  return (
    <div className="card-elev p-4" data-testid={`subject-topic-${t.subject_id}`}>
      <div className="flex flex-wrap items-center gap-3">
        <div className="heading-font font-semibold text-white flex-1 min-w-[160px]">{t.name}</div>
        <span className={`text-[10px] mono-font px-2 py-0.5 rounded border ${pill}`}>{label}</span>
        <div className="flex items-center gap-4 text-xs mono-font text-gray-400">
          <span>ACC {t.accuracy}%</span><span>{t.correct}/{t.questions} CORRECT</span><span>{t.skipped} SKIPPED</span>
        </div>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <div className="flex-1 h-2 rounded-full bg-gray-800 overflow-hidden"><div className={`h-full bg-gradient-to-r ${bar} transition-[width] duration-700`} style={{ width: `${t.score_pct}%` }} /></div>
        <span className="mono-font text-sm text-white w-14 text-right">{t.score_pct}%</span>
      </div>
    </div>
  );
};

export default function WeakTopics() {
  const [d, setD] = useState(null);
  const [view, setView] = useState("section");
  useEffect(() => { api.get("/my/weak-topics").then((r) => setD(r.data)); }, []);
  if (!d) return null;
  const weakest = d.topics.find((t) => t.level !== "strong");
  const subjects = d.subjects || [];

  return (
    <section className="mt-10" data-testid="weak-topics">
      <div className="flex flex-wrap items-end justify-between gap-2 mb-4">
        <div>
          <h2 className="heading-font text-xl font-semibold text-white flex items-center gap-2"><Target className="w-5 h-5 text-cyan-300" />Weak topic report</h2>
          <p className="text-sm text-gray-400 mt-1">
            {d.topics.length ? `Based on ${d.results_analyzed} sectional mock${d.results_analyzed === 1 ? "" : "s"}. ${weakest ? `Focus on ${weakest.name} first.` : "You're strong across every section — keep it up."}` : ""}
          </p>
        </div>
        <div className="flex rounded-md border border-gray-800 p-0.5 text-xs" role="tablist">
          {[["section", "By section"], ["subject", "By subject"]].map(([k, l]) => (
            <button key={k} type="button" onClick={() => setView(k)} data-testid={`weak-view-${k}`}
                    className={`px-3 py-1.5 rounded transition-colors ${view === k ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"}`}>{l}</button>
          ))}
        </div>
      </div>
      {view === "subject" ? (
        subjects.length === 0 ? (
          <div className="card-elev p-6 text-sm text-gray-400" data-testid="subject-topics-empty">No subject-tagged questions attempted yet. Attempt a mock to see your subject-wise accuracy.</div>
        ) : <div className="space-y-3" data-testid="subject-topics">{subjects.map((t) => <SubjectRow key={t.subject_id} t={t} />)}</div>
      ) : d.topics.length === 0 ? (
        <div className="card-elev p-6 text-sm text-gray-400" data-testid="weak-topics-empty">
          Take a sectional mock (Quant, Reasoning, English, GA) to unlock your topic-wise report. <Link to="/test-series" className="text-blue-400">Find one →</Link>
        </div>
      ) : (
        <div className="space-y-3">{d.topics.map((t) => <TopicRow key={t.name} t={t} />)}</div>
      )}
    </section>
  );
}
