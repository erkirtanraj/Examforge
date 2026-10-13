import React from "react";

export default function SectionBreakdown({ sections }) {
  if (!sections || sections.length < 2) return null;
  return (
    <div className="card-elev mt-6 overflow-x-auto" data-testid="section-breakdown">
      <div className="px-5 pt-5 text-xs text-cyan-300 mono-font uppercase tracking-wider">Section-wise performance</div>
      <table className="w-full text-sm mt-3">
        <thead className="bg-gray-900/60"><tr className="text-left text-gray-400 mono-font text-xs uppercase">
          {["Section", "Score", "Correct", "Wrong", "Skipped", "Accuracy"].map((h) => <th key={h} className="p-3 font-medium">{h}</th>)}
        </tr></thead>
        <tbody>
          {sections.map((s, i) => {
            const pct = s.total_marks ? Math.max(0, (s.score / s.total_marks) * 100) : 0;
            return (
              <tr key={i} className="border-t border-gray-800" data-testid={`section-result-${i}`}>
                <td className="p-3 text-white">{s.name}</td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <span className="mono-font text-white w-16">{s.score}/{s.total_marks}</span>
                    <div className="w-24 h-1.5 rounded-full bg-gray-800 overflow-hidden"><div className="h-full bg-gradient-to-r from-blue-500 to-cyan-400" style={{ width: `${pct}%` }} /></div>
                  </div>
                </td>
                <td className="p-3 mono-font text-emerald-300">{s.correct}</td>
                <td className="p-3 mono-font text-rose-300">{s.wrong}</td>
                <td className="p-3 mono-font text-gray-400">{s.unattempted}</td>
                <td className="p-3 mono-font text-gray-300">{s.accuracy}%</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
