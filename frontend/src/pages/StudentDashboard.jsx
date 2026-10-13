import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { BookOpen, Target, TrendingUp, Trophy, FileText, ArrowRight } from "lucide-react";

export default function StudentDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [attempts, setAttempts] = useState([]);
  const [ents, setEnts] = useState([]);

  useEffect(() => {
    api.get("/my/dashboard").then((r) => setStats(r.data));
    api.get("/my/attempts").then((r) => setAttempts(r.data));
    api.get("/my/entitlements").then((r) => setEnts(r.data));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
      <div className="fade-in">
        <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mb-2">Dashboard</div>
        <h1 className="heading-font text-3xl font-bold text-white">Welcome back, {user?.name?.split(" ")[0]}</h1>
        <p className="text-gray-400 mt-1">Here's your learning snapshot.</p>
      </div>

      <div className="mt-8 grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={<FileText className="w-5 h-5" />} label="Tests Attempted" value={stats?.attempts ?? "—"} color="blue" testid="stat-attempts" />
        <StatCard icon={<Trophy className="w-5 h-5" />} label="Submitted" value={stats?.submitted ?? "—"} color="emerald" testid="stat-submitted" />
        <StatCard icon={<Target className="w-5 h-5" />} label="Avg. Accuracy" value={stats ? `${stats.avg_accuracy}%` : "—"} color="cyan" testid="stat-accuracy" />
        <StatCard icon={<BookOpen className="w-5 h-5" />} label="Courses Enrolled" value={stats?.courses_enrolled ?? "—"} color="violet" testid="stat-courses" />
      </div>

      <div className="mt-10 grid lg:grid-cols-3 gap-6">
        <section className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="heading-font text-xl font-semibold text-white">Recent attempts</h2>
            <Link to="/test-series" className="text-sm text-blue-400 hover:text-blue-300">Browse all →</Link>
          </div>
          <div className="space-y-3" data-testid="recent-attempts">
            {attempts.length === 0 && (
              <div className="card-elev p-8 text-center text-gray-400">
                No attempts yet. <Link to="/test-series" className="text-blue-400">Start a free test</Link>.
              </div>
            )}
            {attempts.slice(0, 8).map((a) => (
              <Link key={a.id} to={a.status === "submitted" ? `/result/${a.id}` : `/exam/${a.id}`}
                    className="card-elev p-4 flex items-center justify-between hover:border-blue-500/40">
                <div>
                  <div className="text-white font-medium">{a.test_title}</div>
                  <div className="text-xs text-gray-400 mono-font mt-1 uppercase">
                    {a.status} · {new Date(a.started_at).toLocaleDateString()}
                  </div>
                </div>
                <div className={`text-xs mono-font px-2 py-1 rounded border
                  ${a.status === "submitted" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-amber-500/40 bg-amber-500/10 text-amber-300"}`}>
                  {a.status === "submitted" ? "VIEW RESULT" : "RESUME"} <ArrowRight className="w-3 h-3 inline" />
                </div>
              </Link>
            ))}
          </div>
        </section>

        <aside>
          <div className="flex items-center justify-between mb-4">
            <h2 className="heading-font text-xl font-semibold text-white">My library</h2>
          </div>
          <div className="space-y-3">
            {ents.length === 0 && <div className="card-elev p-4 text-sm text-gray-400">No purchases yet.</div>}
            {ents.map((e) => (
              <div key={e.id} className="card-elev p-4">
                <div className="text-xs text-gray-400 mono-font uppercase">{e.item_type.replace("_", " ")}</div>
                <div className="text-white font-medium text-sm">#{e.item_id.slice(0, 8)}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {e.expires_at ? `Expires ${new Date(e.expires_at).toLocaleDateString()}` : "Lifetime"}
                </div>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}

const StatCard = ({ icon, label, value, color, testid }) => {
  const map = {
    blue: "text-blue-400 border-blue-500/30 bg-blue-500/5",
    cyan: "text-cyan-400 border-cyan-500/30 bg-cyan-500/5",
    emerald: "text-emerald-400 border-emerald-500/30 bg-emerald-500/5",
    violet: "text-violet-400 border-violet-500/30 bg-violet-500/5",
  };
  return (
    <div className={`rounded-xl border p-4 ${map[color]}`} data-testid={testid}>
      <div className="flex items-center gap-2 text-xs mono-font uppercase tracking-wider opacity-90">{icon}{label}</div>
      <div className="text-2xl font-bold text-white mt-2">{value}</div>
    </div>
  );
};
