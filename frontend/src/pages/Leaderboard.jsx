import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Trophy, Users, TrendingUp, Clock, Radio, Crown } from "lucide-react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";

const mmss = (s) => (s == null ? "—" : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`);
const PODIUM = [
  { place: 1, cls: "from-amber-400/25 border-amber-400/50 text-amber-300 md:-translate-y-4" },
  { place: 2, cls: "from-gray-300/15 border-gray-400/40 text-gray-200" },
  { place: 3, cls: "from-orange-500/15 border-orange-500/40 text-orange-300" },
];

const Stat = ({ icon: Icon, label, value, testid }) => (
  <div className="card-elev p-4" data-testid={testid}>
    <div className="text-xs mono-font uppercase text-cyan-300 flex items-center gap-1.5"><Icon className="w-4 h-4" />{label}</div>
    <div className="text-2xl font-bold text-white mt-1">{value ?? "—"}</div>
  </div>
);

export default function Leaderboard() {
  const { testId } = useParams();
  const [d, setD] = useState(null);
  const load = useCallback(() => api.get(`/tests/${testId}/leaderboard?limit=100`).then((r) => setD(r.data)), [testId]);
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);

  if (!d) return <div className="max-w-6xl mx-auto px-4 py-16 text-gray-400">Loading leaderboard…</div>;
  const order = [1, 0, 2].map((i) => d.entries[i]).filter(Boolean);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4 fade-in">
        <div>
          <Link to="/leaderboard" className="text-xs text-gray-500 hover:text-gray-300 mono-font uppercase">← All leaderboards</Link>
          <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mt-3">{d.series?.title}</div>
          <h1 className="heading-font text-3xl font-bold text-white" data-testid="leaderboard-title">{d.test.title}</h1>
          {d.test.sections?.length > 1 && <div className="text-sm text-gray-400 mt-1">{d.test.sections.join(" · ")}</div>}
        </div>
        <div className="flex items-center gap-1.5 text-xs mono-font text-emerald-300"><Radio className="w-3.5 h-3.5 animate-pulse" />LIVE · refreshes every 30s</div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
        <Stat icon={Users} label="Aspirants" value={d.participants} testid="lb-participants" />
        <Stat icon={Trophy} label="Top score" value={d.top_score != null ? `${d.top_score}/${d.test.total_marks}` : null} testid="lb-top" />
        <Stat icon={TrendingUp} label="Average" value={d.avg_score} testid="lb-avg" />
        <Stat icon={Clock} label="Duration" value={`${d.test.duration_minutes} min`} testid="lb-duration" />
      </div>

      {d.me ? (
        <div className="mt-6 card-elev p-5 border-blue-500/40 bg-blue-500/5 flex flex-wrap items-center gap-6" data-testid="lb-me">
          <div><div className="text-xs mono-font text-cyan-300 uppercase">Your rank</div><div className="heading-font text-4xl font-extrabold text-white">#{d.me.rank}</div></div>
          <div><div className="text-xs mono-font text-gray-400 uppercase">Score</div><div className="text-xl font-bold text-white">{d.me.score}</div></div>
          <div><div className="text-xs mono-font text-gray-400 uppercase">Percentile</div><div className="text-xl font-bold text-white">{d.me.percentile}</div></div>
          <div className="text-sm text-gray-400 flex-1 min-w-[200px]">
            {d.me.rank === 1 ? "You're at the top. Defend it — others are attempting right now." : `${d.me.rank - 1} aspirant${d.me.rank === 2 ? "" : "s"} ahead of you. Try the next mock in the series to climb.`}
          </div>
        </div>
      ) : (
        <div className="mt-6 card-elev p-5 flex flex-wrap items-center justify-between gap-4" data-testid="lb-cta">
          <div className="text-gray-300">Take this mock to get your All-India rank.</div>
          <Link to={`/test-series/${d.series?.id}`}><Button className="bg-blue-600 hover:bg-blue-700" data-testid="lb-take-test-btn">Take the test</Button></Link>
        </div>
      )}

      {order.length > 0 && (
        <div className="grid grid-cols-3 gap-3 md:gap-6 mt-12 items-end" data-testid="lb-podium">
          {order.map((e) => {
            const p = PODIUM[e.rank - 1] || PODIUM[2];
            return (
              <div key={e.rank + e.name} className={`rounded-xl border bg-gradient-to-b to-transparent p-4 text-center ${p.cls}`}>
                {e.rank === 1 && <Crown className="w-6 h-6 mx-auto mb-1" />}
                <div className="heading-font text-3xl font-extrabold">#{e.rank}</div>
                <div className="text-white font-medium mt-1 truncate">{e.name}{e.is_you && <span className="text-cyan-300 text-xs ml-1">(you)</span>}</div>
                <div className="mono-font text-sm text-gray-300 mt-1">{e.score} pts</div>
              </div>
            );
          })}
        </div>
      )}

      <div className="card-elev mt-8 overflow-x-auto" data-testid="lb-table">
        <table className="w-full text-sm">
          <thead className="bg-gray-900/60"><tr className="text-left text-gray-400 mono-font text-xs uppercase">
            {["Rank", "Aspirant", "Score", "Accuracy", "Time", "Percentile"].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}
          </tr></thead>
          <tbody>
            {d.entries.map((e, i) => (
              <tr key={i} className={`border-t border-gray-800 ${e.is_you ? "bg-blue-500/10" : ""}`} data-testid={`lb-row-${i + 1}`}>
                <td className="p-3 mono-font font-semibold text-white">#{e.rank}</td>
                <td className="p-3 text-gray-200">{e.name}{e.is_you && <span className="text-cyan-300 text-xs ml-1">(you)</span>}</td>
                <td className="p-3 mono-font text-white">{e.score}</td>
                <td className="p-3 mono-font text-gray-300">{e.accuracy ?? "—"}%</td>
                <td className="p-3 mono-font text-gray-400">{mmss(e.time_taken_sec)}</td>
                <td className="p-3 mono-font text-gray-300">{e.percentile}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!d.entries.length && <div className="p-10 text-center text-gray-500">No attempts yet — be the first on the board.</div>}
      </div>
    </div>
  );
}
