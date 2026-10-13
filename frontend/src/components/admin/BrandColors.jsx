import React from "react";
import { Paintbrush, RotateCcw, Check } from "lucide-react";
import { PRESETS, DEFAULT_THEME, themeVars } from "../../lib/theme";
import { Field } from "./kit";

const ColorInput = ({ label, value, onChange, testid }) => (
  <Field label={label}>
    <div className="mt-1.5 flex items-center gap-2">
      <input type="color" value={value} onChange={(e) => onChange(e.target.value)} className="w-11 h-10 rounded border border-gray-800 bg-transparent cursor-pointer" data-testid={`${testid}-picker`} />
      <input value={value} maxLength={7} onChange={(e) => onChange(e.target.value)} className="w-28 px-3 py-2 rounded-md bg-[#0b1120] border border-gray-800 text-white text-sm mono-font normal-case focus:outline-none focus:border-blue-500" data-testid={`${testid}-hex`} />
    </div>
  </Field>
);

const Preview = ({ theme }) => (
  <div style={themeVars(theme)} className="rounded-lg border border-gray-800 bg-[#090D16] p-5 space-y-4" data-testid="theme-preview">
    <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider">Live preview</div>
    <div className="heading-font text-2xl font-extrabold text-white">Crack exams with a <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-300">precision engine</span></div>
    <div className="flex flex-wrap items-center gap-3">
      <span className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm">Primary button</span>
      <span className="px-4 py-2 rounded-md border border-blue-500/40 bg-blue-500/10 text-blue-300 text-sm">Outline</span>
      <span className="px-2.5 py-1 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 text-xs mono-font">LIVE BADGE</span>
      <span className="text-sm text-blue-400 underline">A link</span>
    </div>
  </div>
);

export default function BrandColors({ theme, onChange }) {
  const t = { ...DEFAULT_THEME, ...theme };
  const valid = (v) => /^#[0-9a-fA-F]{6}$/.test(v);
  return (
    <section className="card-elev p-6 space-y-5" data-testid="brand-colors-settings">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 heading-font font-semibold text-white"><Paintbrush className="w-5 h-5 text-cyan-300" />Brand colours</div>
        <button type="button" onClick={() => onChange(DEFAULT_THEME)} className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors" data-testid="theme-reset">
          <RotateCcw className="w-3.5 h-3.5" /> Reset to default
        </button>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {PRESETS.map((p) => (
          <button key={p.id} type="button" onClick={() => onChange({ preset: p.id, primary: p.primary, accent: p.accent })} data-testid={`theme-preset-${p.id}`}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-md border text-sm text-left transition-colors ${t.preset === p.id ? "border-white/60 bg-white/5 text-white" : "border-gray-800 text-gray-300 hover:border-gray-600"}`}>
            <span className="flex -space-x-1.5 shrink-0">
              <span className="w-5 h-5 rounded-full border-2 border-[#111827]" style={{ background: p.primary }} />
              <span className="w-5 h-5 rounded-full border-2 border-[#111827]" style={{ background: p.accent }} />
            </span>
            <span className="flex-1">{p.name}</span>
            {t.preset === p.id && <Check className="w-4 h-4" />}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap gap-6">
        <ColorInput label="Main colour" value={t.primary} onChange={(v) => onChange({ ...t, preset: "custom", primary: v })} testid="theme-primary" />
        <ColorInput label="Accent colour" value={t.accent} onChange={(v) => onChange({ ...t, preset: "custom", accent: v })} testid="theme-accent" />
      </div>
      {valid(t.primary) && valid(t.accent) ? <Preview theme={t} /> : <p className="text-sm text-rose-300">Enter colours as 6-digit hex, e.g. #2563eb</p>}
      <p className="text-xs text-gray-500">Main colour drives buttons, links and the admin menu; accent colours badges and highlights. Saved colours apply to the whole site.</p>
    </section>
  );
}
