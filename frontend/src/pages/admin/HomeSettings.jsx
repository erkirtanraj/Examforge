import React from "react";
import { Loader2, Sparkles, BarChart3, LayoutGrid } from "lucide-react";
import { PageHeader, Field, inputCls } from "../../components/admin/kit";
import ListEditor from "../../components/admin/ListEditor";
import useSiteForm from "../../components/admin/useSiteForm";
import { FEATURE_ICONS } from "../../lib/featureIcons";
import { Button } from "../../components/ui/button";

const SOURCES = [
  { value: "students", label: "Students (live)" }, { value: "questions", label: "Questions (live)" },
  { value: "tests", label: "Tests (live)" }, { value: "attempts", label: "Attempts (live)" },
  { value: "live", label: "Attempting now" }, { value: "manual", label: "Manual only" },
];
const HERO = [
  ["badge_text", "Badge text — {live} = students attempting now"], ["title", "Headline"], ["highlight", "Highlighted words (gradient)"],
  ["primary_cta_label", "Primary button label"], ["primary_cta_url", "Primary button link"],
  ["secondary_cta_label", "Secondary button label"], ["secondary_cta_url", "Secondary button link"],
];
const ICON_OPTS = Object.keys(FEATURE_ICONS).map((k) => ({ value: k, label: k }));
const Card = ({ icon: Icon, title, children, testid }) => (
  <section className="card-elev p-6 space-y-4" data-testid={testid}>
    <div className="flex items-center gap-2 heading-font font-semibold text-white"><Icon className="w-5 h-5 text-cyan-300" />{title}</div>
    {children}
  </section>
);

export default function HomeSettings() {
  const { form, set, save, saving, metrics } = useSiteForm("/admin/site/home", ["hero", "stats", "features"]);
  if (!form) return <div className="text-gray-400 text-sm">Loading…</div>;
  const { hero } = form;
  return (
    <div className="max-w-4xl">
      <PageHeader eyebrow="System" title="Home Page" desc="Edit the landing page hero, stats and feature highlights." />
      <form onSubmit={save} className="space-y-6">
        <Card icon={Sparkles} title="Hero" testid="hero-settings">
          <div className="grid sm:grid-cols-2 gap-4">
            {HERO.map(([k, label]) => (
              <Field key={k} label={label} className={k === "badge_text" ? "sm:col-span-2" : ""}>
                <input value={hero[k]} onChange={(e) => set("hero", { [k]: e.target.value })} className={inputCls} data-testid={`hero-${k}`} />
              </Field>
            ))}
            <Field label="Sub-heading" className="sm:col-span-2">
              <textarea rows={3} value={hero.subtitle} onChange={(e) => set("hero", { subtitle: e.target.value })} className={inputCls} data-testid="hero-subtitle" />
            </Field>
          </div>
        </Card>

        <Card icon={BarChart3} title="Hero stats" testid="stats-settings">
          <p className="text-sm text-gray-400">Live sources count from your database. Type an override (e.g. “250K+”) to show your own number instead.</p>
          <div className="flex flex-wrap gap-2 text-xs mono-font" data-testid="live-metrics">
            {Object.entries(metrics).map(([k, v]) => <span key={k} className="px-2 py-1 rounded border border-gray-800 text-gray-300">{k}: {v}</span>)}
          </div>
          <ListEditor items={form.stats} onChange={(v) => set("stats", v)} max={6} testid="stats-editor" addLabel="Add stat"
                      blank={{ label: "", source: "manual", override: "" }}
                      fields={[{ key: "label", placeholder: "Label" }, { key: "source", type: "select", options: SOURCES }, { key: "override", placeholder: "Override (optional)" }]} />
        </Card>

        <Card icon={LayoutGrid} title="Feature highlights" testid="features-settings">
          <ListEditor items={form.features} onChange={(v) => set("features", v)} max={9} testid="features-editor" addLabel="Add feature"
                      blank={{ icon: "Target", title: "", desc: "" }}
                      fields={[{ key: "icon", type: "select", options: ICON_OPTS }, { key: "title", placeholder: "Title" }, { key: "desc", placeholder: "Description", wide: true }]} />
        </Card>

        <Button type="submit" disabled={saving} className="bg-blue-600 hover:bg-blue-700" data-testid="save-home-settings">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save home page"}
        </Button>
      </form>
    </div>
  );
}
