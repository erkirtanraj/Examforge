import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

export default function CourseCatalog() {
  const [list, setList] = useState([]);
  useEffect(() => { api.get("/courses").then((r) => setList(r.data)); }, []);
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
      <div className="mb-8 fade-in">
        <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mb-2">Courses</div>
        <h1 className="heading-font text-3xl font-bold text-white">Learn from top faculty</h1>
        <p className="text-gray-400 mt-2">Structured video courses, notes and practice built into one path.</p>
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {list.map((c) => (
          <Link key={c.id} to={`/courses/${c.id}`} data-testid={`course-card-${c.id}`} className="card-elev overflow-hidden hover:border-blue-500/40">
            <div className="aspect-video bg-gray-800">
              {c.thumbnail && <img src={c.thumbnail} alt="" className="w-full h-full object-cover" />}
            </div>
            <div className="p-5">
              <div className="heading-font text-lg font-semibold text-white">{c.title}</div>
              <div className="text-sm text-gray-400 mt-2 line-clamp-2">{c.description}</div>
              <div className="mt-4 flex items-center justify-between">
                <span className={`text-xs mono-font px-2 py-0.5 rounded border ${c.is_free ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30" : "bg-amber-500/10 text-amber-300 border-amber-500/30"}`}>
                  {c.is_free ? "FREE" : "PREMIUM"}
                </span>
                <span className="heading-font text-lg font-bold text-cyan-300">
                  {c.is_free ? "Enroll" : `₹${(c.price / 100).toFixed(0)}`}
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
