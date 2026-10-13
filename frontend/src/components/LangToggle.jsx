import React from "react";

export default function LangToggle({ lang, onChange, testid = "lang-toggle" }) {
  return (
    <div className="inline-flex rounded-md border border-gray-700 overflow-hidden text-xs" data-testid={testid}>
      {[["en", "EN"], ["hi", "हिं"]].map(([k, l]) => (
        <button key={k} type="button" onClick={() => onChange(k)} data-testid={`${testid}-${k}`}
                className={`px-3 py-1.5 transition-colors ${lang === k ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-gray-800"}`}>
          {l}
        </button>
      ))}
    </div>
  );
}

export const pick = (lang, en, hi) => (lang === "hi" && hi) || en;
