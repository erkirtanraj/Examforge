import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Trophy, Users, Layers } from "lucide-react";
import { api } from "../lib/api";

export default function Leaderboards() {
  const [list, setList] = useState(null);
  useEffect(() => { api.get("/leaderboards").then((r) => setList(r.data)); }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
      <div className="mb-8 fade-in">
        <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mb-2">Leaderboard</div>
        <h1 className="heading-font text-3xl font-bold text-white">Where do you stand nationally?</h1>
        <p className="text-gray-400 mt-2">Live All-India rankings for every mock. Ranks use each aspirant's first attempt.</p>
      </div>
      {!list && <div className="text-gray-400">Loading…</div>}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="leaderboards-grid">
        {list?.map((t) => (
          <Link key={t.id} to={`/leaderboard/${t.id}`} data-testid={`leaderboard-card-${t.id}`} className="card-elev p-5 hover:border-blue-500/40 group">
            <div className="text-xs text-gray-500 mono-font uppercase truncate">{t.series_title}</div>
            <div className="heading-font text-base font-semibold text-white mt-1 group-hover:text-cyan-300 transition-colors">{t.title}</div>
            <div className="mt-4 flex items-center gap-4 text-xs mono-font text-gray-400">
              <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" />{t.participants}</span>
              {t.top_score != null && <span className="flex items-center gap-1 text-amber-300"><Trophy className="w-3.5 h-3.5" />{t.top_score}/{t.total_marks}</span>}
              {t.sections > 1 && <span className="flex items-center gap-1"><Layers className="w-3.5 h-3.5" />{t.sections} sections</span>}
            </div>
            {t.participants === 0 && <div className="mt-3 text-xs text-emerald-300">Be the first to set the top score</div>}
          </Link>
        ))}
      </div>
    </div>
  );
}
