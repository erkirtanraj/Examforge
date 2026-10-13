import React from "react";
import { Loader2, PanelTop, PanelBottom } from "lucide-react";
import { PageHeader, Field, inputCls } from "../../components/admin/kit";
import ListEditor from "../../components/admin/ListEditor";
import useSiteForm from "../../components/admin/useSiteForm";
import { Button } from "../../components/ui/button";

const LINK_FIELDS = [{ key: "label", placeholder: "Label" }, { key: "url", placeholder: "/path or https://…", wide: true }];
const Input = ({ label, value, onChange, testid }) => (
  <Field label={label}><input value={value} onChange={(e) => onChange(e.target.value)} className={inputCls} data-testid={testid} /></Field>
);

export default function SiteSettings() {
  const { form, set, save, saving } = useSiteForm("/admin/site/layout", ["header", "footer"]);
  if (!form) return <div className="text-gray-400 text-sm">Loading…</div>;
  const { header, footer } = form;
  return (
    <div className="max-w-3xl">
      <PageHeader eyebrow="System" title="Site Settings" desc="Header and footer shown on every public page. Use /page/<slug> to link legal pages." />
      <form onSubmit={save} className="space-y-6">
        <section className="card-elev p-6 space-y-4" data-testid="header-settings">
          <div className="flex items-center gap-2 heading-font font-semibold text-white"><PanelTop className="w-5 h-5 text-cyan-300" />Header</div>
          <Input label="Brand name" value={header.brand_name} onChange={(v) => set("header", { brand_name: v })} testid="site-brand-name" />
          <Field label="Menu links" />
          <ListEditor items={header.nav_links} onChange={(v) => set("header", { nav_links: v })} fields={LINK_FIELDS} blank={{ label: "", url: "/" }} testid="nav-links-editor" max={8} addLabel="Add menu link" />
          <div className="grid sm:grid-cols-2 gap-4">
            <Input label="Button label (logged out)" value={header.cta_label} onChange={(v) => set("header", { cta_label: v })} testid="site-cta-label" />
            <Input label="Button link" value={header.cta_url} onChange={(v) => set("header", { cta_url: v })} testid="site-cta-url" />
          </div>
        </section>

        <section className="card-elev p-6 space-y-4" data-testid="footer-settings">
          <div className="flex items-center gap-2 heading-font font-semibold text-white"><PanelBottom className="w-5 h-5 text-cyan-300" />Footer</div>
          <Input label="Tagline" value={footer.tagline} onChange={(v) => set("footer", { tagline: v })} testid="site-footer-tagline" />
          <Input label="Copyright text" value={footer.copyright} onChange={(v) => set("footer", { copyright: v })} testid="site-footer-copyright" />
          <Field label="Footer links" />
          <ListEditor items={footer.links} onChange={(v) => set("footer", { links: v })} fields={LINK_FIELDS} blank={{ label: "", url: "/page/" }} testid="footer-links-editor" max={12} addLabel="Add footer link" />
        </section>

        <Button type="submit" disabled={saving} className="bg-blue-600 hover:bg-blue-700" data-testid="save-site-settings">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save site settings"}
        </Button>
      </form>
    </div>
  );
}
