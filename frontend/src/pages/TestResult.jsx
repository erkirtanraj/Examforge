import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Trophy, Target, Clock, CheckCircle2, XCircle, MinusCircle } from "lucide-react";

export default function TestResult() {
  const { attemptId } = useParams();
  const [r, setR] = useState(null);

  useEffect(() => {
    api.get(`/attempts/${attemptId}/result`).then((x) => setR(x.data));
  }, [attemptId]);

  if (!r) return <div className="max-w-5xl mx-auto p-8 text-gray-400">Loading result…</div>;

  const pct = r.total_marks ? Math.round((r.score / r.total_marks) * 100) : 0;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
      <div className="card-elev p-6 sm:p-8 relative overflow-hidden fade-in">
        <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-blue-600/20 blur-3xl" />
        <div className="relative grid md:grid-cols-4 gap-6">
          <div className="md:col-span-2">
            <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mb-1">Result</div>
            <h1 className="heading-font text-3xl font-bold text-white">Score: {r.score} / {r.total_marks}</h1>
            <p className="text-gray-400 mt-1">Attempt completed · {new Date(r.created_at).toLocaleString()}</p>
            <div className="mt-4 flex items-center gap-3">
              <div className="w-full max-w-md h-3 rounded-full bg-gray-800 overflow-hidden">
                <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-400" style={{ width: `${pct}%` }} />
              </div>
              <span className="text-sm text-cyan-300 mono-font font-semibold">{pct}%</span>
            </div>
          </div>
          <StatCard icon={<Target className="w-5 h-5" />} label="Accuracy" value={`${r.accuracy}%`} color="cyan" />
          <StatCard icon={<Trophy className="w-5 h-5" />} label="Correct" value={r.correct} color="emerald" />
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4 mt-6">
        <div className="card-elev p-5 flex items-center gap-3">
          <CheckCircle2 className="w-6 h-6 text-emerald-400" />
          <div><div className="text-xs text-gray-400 mono-font uppercase">Correct</div><div className="text-xl font-bold text-white">{r.correct}</div></div>
        </div>
        <div className="card-elev p-5 flex items-center gap-3">
          <XCircle className="w-6 h-6 text-rose-400" />
          <div><div className="text-xs text-gray-400 mono-font uppercase">Wrong</div><div className="text-xl font-bold text-white">{r.wrong}</div></div>
        </div>
        <div className="card-elev p-5 flex items-center gap-3">
          <MinusCircle className="w-6 h-6 text-gray-400" />
          <div><div className="text-xs text-gray-400 mono-font uppercase">Unattempted</div><div className="text-xl font-bold text-white">{r.unattempted}</div></div>
        </div>
      </div>

      <h2 className="heading-font text-xl font-semibold text-white mt-10 mb-4">Answer review</h2>
      <div className="space-y-4">
        {r.questions?.map((q, i) => {
          const yours = r.user_answers?.[q.id];
          const correct = q.correct || [];
          const yoursArr = Array.isArray(yours) ? yours : yours !== undefined ? [yours] : [];
          const isCorrect = JSON.stringify([...yoursArr].sort()) === JSON.stringify([...correct].sort());
          return (
            <div key={q.id} className="card-elev p-5" data-testid={`review-q-${i + 1}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs text-gray-400 mono-font">Q.{i + 1}</div>
                <div className={`text-xs mono-font px-2 py-0.5 rounded border ${
                  yoursArr.length === 0 ? "border-gray-700 text-gray-400" :
                  isCorrect ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-rose-500/40 bg-rose-500/10 text-rose-300"
                }`}>
                  {yoursArr.length === 0 ? "UNATTEMPTED" : isCorrect ? "CORRECT" : "WRONG"}
                </div>
              </div>
              <div className="text-white font-medium">{q.text}</div>
              <div className="mt-3 space-y-1.5">
                {q.options?.map((o) => {
                  const isAns = correct.includes(o.key);
                  const isUserSel = yoursArr.includes(o.key);
                  return (
                    <div key={o.key} className={`p-2 rounded border text-sm ${
                      isAns ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-200" :
                      isUserSel ? "border-rose-500/50 bg-rose-500/10 text-rose-200" :
                      "border-gray-800 text-gray-400"
                    }`}>
                      <span className="mono-font mr-2">{o.key}.</span>{o.text}
                      {isAns && <span className="ml-2 text-xs mono-font">✓ CORRECT</span>}
                      {isUserSel && !isAns && <span className="ml-2 text-xs mono-font">YOUR ANSWER</span>}
                    </div>
                  );
                })}
              </div>
              {q.explanation && (
                <div className="mt-3 p-3 rounded-md bg-blue-500/5 border border-blue-500/20 text-sm text-blue-100">
                  <span className="mono-font text-xs text-blue-300 uppercase tracking-wider">Explanation</span>
                  <div className="mt-1">{q.explanation}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-8 flex gap-3">
        <Link to="/dashboard"><Button variant="outline" className="border-gray-700 bg-transparent text-gray-200 hover:bg-gray-800">Back to Dashboard</Button></Link>
        <Link to="/test-series"><Button className="bg-blue-600 hover:bg-blue-700">Attempt more tests</Button></Link>
      </div>
    </div>
  );
}

const StatCard = ({ icon, label, value, color }) => (
  <div className={`rounded-xl border p-4 bg-${color}-500/5 border-${color}-500/30`}>
    <div className={`text-${color}-300 flex items-center gap-2 text-xs mono-font uppercase tracking-wider`}>{icon}{label}</div>
    <div className="text-2xl font-bold text-white mt-1">{value}</div>
  </div>
);
