import React from "react";
import { Medal, Users } from "lucide-react";

export default function RankCard({ rank }) {
  if (!rank) return null;
  return (
    <div className="card-elev p-6 mt-6 relative overflow-hidden" data-testid="rank-card">
      <div className="absolute -bottom-20 -left-20 w-64 h-64 rounded-full bg-cyan-500/10 blur-3xl" />
      <div className="relative grid md:grid-cols-3 gap-6">
        <div>
          <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider flex items-center gap-1.5"><Medal className="w-4 h-4" />All-India Rank</div>
          <div className="heading-font text-5xl font-extrabold text-white mt-2" data-testid="air-rank">#{rank.rank}</div>
          <div className="text-sm text-gray-400 mt-1 flex items-center gap-1.5" data-testid="air-total"><Users className="w-4 h-4" />of {rank.total} aspirant{rank.total === 1 ? "" : "s"}</div>
        </div>
        <div>
          <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider">Percentile</div>
          <div className="heading-font text-5xl font-extrabold text-white mt-2" data-testid="air-percentile">{rank.percentile}</div>
          <div className="mt-3 h-2 rounded-full bg-gray-800 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 transition-[width] duration-700" style={{ width: `${rank.percentile}%` }} />
          </div>
          <div className="text-xs text-gray-400 mt-2">
            {rank.total > 1 ? `You scored higher than ${rank.percentile}% of other aspirants.` : "You're the first to take this test — rank updates as others attempt."}
          </div>
        </div>
        <div>
          <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mb-2">Top performers</div>
          <div className="space-y-1.5" data-testid="leaderboard">
            {rank.top.map((t, i) => (
              <div key={i} className={`flex items-center gap-3 text-sm px-2 py-1.5 rounded ${t.is_you ? "bg-blue-500/10 border border-blue-500/30" : ""}`}>
                <span className="mono-font text-xs text-gray-400 w-6">#{t.rank}</span>
                <span className="flex-1 text-gray-200 truncate">{t.name}{t.is_you && <span className="text-cyan-300 text-xs ml-1">(you)</span>}</span>
                <span className="mono-font text-xs text-white">{t.score}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="relative text-[11px] text-gray-500 mt-5 mono-font">
        {rank.is_official ? "Rank is based on every student's first attempt of this test." : "This was a re-attempt — your rank reflects your first attempt."}
      </div>
    </div>
  );
}
