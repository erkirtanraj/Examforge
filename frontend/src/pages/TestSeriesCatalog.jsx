import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, assetUrl } from "../lib/api";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";

export default function TestSeriesCatalog() {
  const [params] = useSearchParams();
  const [list, setList] = useState([]);
  const [cats, setCats] = useState([]);
  const [cat, setCat] = useState(params.get("category") || "");

  useEffect(() => {
    api.get("/categories").then((r) => setCats(r.data));
  }, []);

  useEffect(() => {
    const q = cat ? `?category_id=${cat}` : "";
    api.get(`/test-series${q}`).then((r) => setList(r.data));
  }, [cat]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
      <div className="mb-8 fade-in">
        <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mb-2">Test Series</div>
        <h1 className="heading-font text-3xl font-bold text-white">Browse all test series</h1>
        <p className="text-gray-400 mt-2">Full-length mocks, sectional tests and previous-year papers.</p>
      </div>

      <div className="flex flex-wrap gap-2 mb-8" data-testid="series-filters">
        <button onClick={() => setCat("")} data-testid="filter-all"
                className={`px-3 py-1.5 rounded-md text-sm border transition-colors ${!cat ? "bg-blue-600 border-blue-500 text-white" : "border-gray-800 text-gray-300 hover:border-gray-600"}`}>
          All Exams
        </button>
        {cats.map((c) => (
          <button key={c.id} onClick={() => setCat(c.id)} data-testid={`filter-${c.slug}`}
                  className={`px-3 py-1.5 rounded-md text-sm border transition-colors ${cat === c.id ? "bg-blue-600 border-blue-500 text-white" : "border-gray-800 text-gray-300 hover:border-gray-600"}`}>
            {c.name}
          </button>
        ))}
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {list.map((s) => (
          <Link key={s.id} to={`/test-series/${s.id}`} data-testid={`series-card-${s.id}`} className="card-elev overflow-hidden hover:border-blue-500/40">
            <div className="aspect-video bg-gray-800 overflow-hidden">
              {s.thumbnail && <img loading="lazy" decoding="async" src={assetUrl(s.thumbnail)} alt="" className="w-full h-full object-cover" />}
            </div>
            <div className="p-5">
              <div className="flex items-center gap-2 mb-3">
                {s.is_free ? (
                  <Badge className="bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/10">FREE</Badge>
                ) : (
                  <Badge className="bg-amber-500/10 text-amber-300 border border-amber-500/30 hover:bg-amber-500/10">PREMIUM</Badge>
                )}
                <span className="text-xs text-gray-400 mono-font">{s.tests_count || 0} TESTS</span>
              </div>
              <div className="heading-font text-lg font-semibold text-white">{s.title}</div>
              <div className="text-sm text-gray-400 mt-2 line-clamp-2">{s.description}</div>
              <div className="mt-4 flex items-center justify-between">
                <span className="text-xs text-gray-500 mono-font uppercase">{s.validity_days} days access</span>
                <span className="heading-font text-lg font-bold text-cyan-300">
                  {s.is_free ? "Free" : `₹${(s.price / 100).toFixed(0)}`}
                </span>
              </div>
            </div>
          </Link>
        ))}
        {list.length === 0 && (
          <div className="col-span-full text-center text-gray-400 py-20">No test series found.</div>
        )}
      </div>
    </div>
  );
}
