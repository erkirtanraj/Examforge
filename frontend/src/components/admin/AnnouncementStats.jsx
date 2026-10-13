import React, { useEffect, useState } from "react";
import { Eye, MousePointerClick, Copy, XCircle, Percent, RefreshCw, BarChart3 } from "lucide-react";
import { api } from "../../lib/api";
import { DataTable, Pill } from "./kit";

const METRICS = [
  ["views", "Views", Eye], ["clicks", "Button clicks", MousePointerClick], ["click_rate", "Click rate", Percent],
  ["copies", "Coupon copies", Copy], ["closes", "Closed", XCircle],
];
const fmt = (k, v) => (k === "click_rate" ? `${v || 0}%` : (v || 0).toLocaleString());

export default function AnnouncementStats({ refreshKey }) {
  const [rows, setRows] = useState(null);
  const load = () => api.get("/admin/announcement/stats").then((r) => setRows(r.data));
  useEffect(() => { load(); }, [refreshKey]);
  if (!rows) return null;
  const cur = rows.find((r) => r.is_current);
  const past = rows.filter((r) => !r.is_current);
  return (
    <section className="space-y-4" data-testid="announcement-stats">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 heading-font font-semibold text-white"><BarChart3 className="w-5 h-5 text-cyan-300" />Banner performance</div>
        <button type="button" onClick={load} className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-white" data-testid="announcement-stats-refresh"><RefreshCw className="w-3.5 h-3.5" /> Refresh</button>
      </div>
      {cur ? (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3" data-testid="announcement-current-stats">
          {METRICS.map(([k, label, Icon]) => (
            <div key={k} className="card-elev p-4">
              <div className="flex items-center gap-1.5 text-[11px] text-gray-400 mono-font uppercase"><Icon className="w-3.5 h-3.5 text-cyan-300" />{label}</div>
              <div className="heading-font text-2xl font-bold text-white mt-1" data-testid={`stat-current-${k}`}>{fmt(k, cur[k])}</div>
            </div>
          ))}
        </div>
      ) : <div className="card-elev p-5 text-sm text-gray-500">No stats yet for the current banner. Save a message to start tracking.</div>}
      {past.length > 0 && (
        <>
          <div className="text-[11px] text-gray-400 mono-font uppercase tracking-wider pt-2">Past banners</div>
          <DataTable testid="announcement-past-stats" head={["Message", "Views", "Clicks", "Rate", "Copies", "Closed"]}>
            {past.map((r) => (
              <tr key={r.version} className="border-t border-gray-800" data-testid={`past-banner-${r.version}`}>
                <td className="p-3 text-white max-w-[260px]">
                  <div className="truncate">{r.message}</div>
                  <div className="mt-1 flex gap-2 items-center"><Pill tone="gray">{r.style.toUpperCase()}</Pill><span className="text-[11px] text-gray-500">{new Date(r.created_at).toLocaleDateString()}</span></div>
                </td>
                {["views", "clicks", "click_rate", "copies", "closes"].map((k) => <td key={k} className="p-3 text-gray-300 mono-font">{fmt(k, r[k])}</td>)}
              </tr>
            ))}
          </DataTable>
        </>
      )}
    </section>
  );
}
