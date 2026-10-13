import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Radio, CalendarClock, ArrowRight, Users } from "lucide-react";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { useNow, fmtCountdown, fmtDateTime } from "./Countdown";

export default function LiveMockBanner() {
  const [data, setData] = useState(null);
  const [offset, setOffset] = useState(0);
  const now = useNow(1000) + offset;
  useEffect(() => {
    api.get("/live-mocks").then((r) => { setOffset(new Date(r.data.server_now).getTime() - Date.now()); setData(r.data.mocks); });
  }, []);

  const mocks = (data || []).filter((m) => new Date(m.live_end_at).getTime() > now);
  if (!mocks.length) return null;
  const [next, ...rest] = mocks;
  const start = new Date(next.live_start_at).getTime();
  const live = now >= start;

  return (
    <section className="max-w-7xl mx-auto px-4 sm:px-6 pt-4" data-testid="live-mock-banner">
      <div className={`relative overflow-hidden rounded-2xl border p-6 sm:p-8 ${live ? "border-rose-500/50 bg-rose-500/5" : "border-cyan-500/30 bg-cyan-500/5"}`}>
        <div className="absolute -right-24 -top-24 w-72 h-72 rounded-full bg-blue-600/20 blur-3xl" />
        <div className="relative grid lg:grid-cols-[1fr_auto] gap-6 items-center">
          <div>
            <div className={`inline-flex items-center gap-2 text-xs mono-font uppercase tracking-wider ${live ? "text-rose-300" : "text-cyan-300"}`}>
              {live ? <><Radio className="w-4 h-4 animate-pulse" />Live now · All-India mock</> : <><CalendarClock className="w-4 h-4" />Upcoming All-India live mock</>}
            </div>
            <h2 className="heading-font text-2xl sm:text-3xl font-bold text-white mt-2" data-testid="live-mock-title">{next.title}</h2>
            <div className="text-sm text-gray-400 mt-2 flex flex-wrap gap-x-4 gap-y-1">
              <span>{fmtDateTime(next.live_start_at)}</span>
              <span>{next.duration_minutes} min · {next.total_marks} marks</span>
              {next.sections?.length > 1 && <span>{next.sections.join(" · ")}</span>}
            </div>
          </div>
          <div className="flex flex-col sm:flex-row lg:flex-col items-start sm:items-center lg:items-end gap-4">
            {!live && (
              <div className="text-right">
                <div className="text-[10px] mono-font text-gray-500 uppercase">Starts in</div>
                <div className="heading-font text-3xl sm:text-4xl font-extrabold text-white mono-font" data-testid="live-mock-countdown">{fmtCountdown(start - now)}</div>
              </div>
            )}
            <Link to={`/test-series/${next.series?.id}`} data-testid="live-mock-cta">
              <Button className={live ? "bg-rose-600 hover:bg-rose-700" : "bg-blue-600 hover:bg-blue-700"}>
                {live ? "Join the live mock" : next.series?.is_free ? "View & get ready" : "Unlock to participate"} <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          </div>
        </div>
        {rest.length > 0 && (
          <div className="relative mt-6 pt-4 border-t border-gray-800 flex flex-wrap gap-x-6 gap-y-2 text-sm">
            <span className="text-xs mono-font text-gray-500 uppercase flex items-center gap-1"><Users className="w-3.5 h-3.5" />Also scheduled</span>
            {rest.slice(0, 3).map((m) => (
              <Link key={m.id} to={`/test-series/${m.series?.id}`} className="text-gray-300 hover:text-white">{m.title} · <span className="text-gray-500">{fmtDateTime(m.live_start_at)}</span></Link>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
