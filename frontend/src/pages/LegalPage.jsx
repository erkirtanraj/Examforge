import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { api } from "../lib/api";

export default function LegalPage() {
  const { slug } = useParams();
  const [page, setPage] = useState(undefined);
  useEffect(() => {
    setPage(undefined);
    api.get(`/pages/${slug}`).then((r) => setPage(r.data)).catch(() => setPage(null));
  }, [slug]);

  if (page === undefined) return <div className="app-shell min-h-[60vh] flex items-center justify-center text-gray-400">Loading…</div>;
  return (
    <div className="app-shell min-h-[60vh]">
      <article className="max-w-3xl mx-auto px-4 sm:px-6 py-16 fade-in" data-testid="legal-page">
        {page ? (
          <>
            <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mb-2">Updated {new Date(page.updated_at).toLocaleDateString()}</div>
            <h1 className="heading-font text-4xl sm:text-5xl font-extrabold text-white" data-testid="legal-page-title">{page.title}</h1>
            <div className="legal-prose mt-8" data-testid="legal-page-content"><ReactMarkdown>{page.content}</ReactMarkdown></div>
          </>
        ) : (
          <h1 className="heading-font text-3xl font-bold text-white" data-testid="legal-page-not-found">Page not found</h1>
        )}
      </article>
    </div>
  );
}
