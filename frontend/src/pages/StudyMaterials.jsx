import React, { useEffect, useState } from "react";
import { api, assetUrl } from "../lib/api";
import { FileText, Download, Lock } from "lucide-react";

export default function StudyMaterials() {
  const [list, setList] = useState([]);
  useEffect(() => { api.get("/study-materials").then((r) => setList(r.data)); }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
      <div className="mb-8 fade-in">
        <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mb-2">Resources</div>
        <h1 className="heading-font text-3xl font-bold text-white">Study materials library</h1>
        <p className="text-gray-400 mt-2">Notes, previous-year papers and answer keys — curated for every exam.</p>
      </div>
      <div className="grid md:grid-cols-2 gap-4" data-testid="materials-grid">
        {list.map((m) => (
          <div key={m.id} className="card-elev p-5 flex flex-col sm:flex-row items-start gap-4" data-testid={`material-card-${m.id}`}>
            {m.thumbnail ? (
              <img loading="lazy" decoding="async" src={assetUrl(m.thumbnail)} alt="" className="w-full sm:w-32 aspect-video rounded-lg object-cover border border-gray-800 shrink-0" data-testid={`material-thumb-${m.id}`} />
            ) : (
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 flex items-center justify-center shrink-0">
                <FileText className="w-6 h-6 text-cyan-300" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <div className="heading-font text-base font-semibold text-white">{m.title}</div>
              <div className="text-sm text-gray-400 mt-1">{m.description}</div>
              <div className="mt-3 flex items-center gap-3">
                {m.is_free ? (
                  <a href={m.file_url} target="_blank" rel="noopener noreferrer"
                     className="inline-flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300" data-testid={`download-${m.id}`}>
                    <Download className="w-4 h-4" /> Download free
                  </a>
                ) : (
                  <span className="inline-flex items-center gap-1 text-sm text-amber-300 mono-font">
                    <Lock className="w-4 h-4" /> ₹{(m.price / 100).toFixed(0)}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
