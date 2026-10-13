import React from "react";
import { Loader2, PanelTop, PanelBottom, Palette, Megaphone, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { useSite } from "../../lib/site";
import ImageField from "../../components/admin/ImageField";
import { Switch } from "../../components/ui/switch";
import { PageHeader, Field, inputCls } from "../../components/admin/kit";
import ListEditor from "../../components/admin/ListEditor";
import useSiteForm from "../../components/admin/useSiteForm";
import { Button } from "../../components/ui/button";

const LINK_FIELDS = [{ key: "label", placeholder: "Label" }, { key: "url", placeholder: "/path or https://…", wide: true }];
const Input = ({ label, value, onChange, testid }) => (
  <Field label={label}><input value={value} onChange={(e) => onChange(e.target.value)} className={inputCls} data-testid={testid} /></Field>
);

export default function SiteSettings() {
  const { site } = useSite();
  const { form, set, save, saving } = useSiteForm("/admin/site/layout", ["header", "footer"]);
  if (!form) return <div className="text-gray-400 text-sm">Loading…</div>;
  const { header, footer } = form;
  const ann = site?.announcement;
  return (
    <div className="max-w-3xl">
      <PageHeader eyebrow="System" title="Site Settings" desc="Logo, header and footer shown on every page. Use /page/<slug> to link legal pages." />
      <form onSubmit={save} className="space-y-6">
        <section className="card-elev p-6 space-y-5" data-testid="branding-settings">
          <div className="flex items-center gap-2 heading-font font-semibold text-white"><Palette className="w-5 h-5 text-cyan-300" />Logo &amp; branding</div>
          <Input label="Brand name" value={header.brand_name} onChange={(v) => set("header", { brand_name: v })} testid="site-brand-name" />
          <ImageField label="Logo" value={header.logo_url} onChange={(v) => set("header", { logo_url: v })} testid="logo" hint="PNG, SVG or WEBP, up to 2 MB. Transparent background, about 36 px tall works best." />
          <ImageField label="Browser tab icon (favicon)" value={header.favicon_url} onChange={(v) => set("header", { favicon_url: v })} testid="favicon" hint="Square image (ICO, PNG or SVG), 32×32 or 64×64." />
          <div className="flex items-center justify-between gap-4 rounded-md border border-gray-800 px-4 py-3">
            <div>
              <div className="text-sm text-white">Show brand name next to logo</div>
              <div className="text-xs text-gray-500">Turn off if your logo already contains the name.</div>
            </div>
            <Switch checked={header.show_brand_name} onCheckedChange={(v) => set("header", { show_brand_name: v })} data-testid="show-brand-name-switch" />
          </div>
        </section>

        <section className="card-elev p-6 space-y-4" data-testid="header-settings">
          <div className="flex items-center gap-2 heading-font font-semibold text-white"><PanelTop className="w-5 h-5 text-cyan-300" />Header</div>
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

        <Link to="/admin/announcement" className="card-elev p-5 flex items-center justify-between gap-4 hover:border-blue-500/40 transition-colors" data-testid="announcement-shortcut">
          <div className="flex items-center gap-3 min-w-0">
            <Megaphone className="w-5 h-5 text-cyan-300 shrink-0" />
            <div className="min-w-0">
              <div className="heading-font font-semibold text-white">Announcement Bar</div>
              <div className="text-xs text-gray-400 truncate">{ann ? `Live: ${ann.message}` : "Not showing — set up a banner for mocks or coupons"}</div>
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-gray-400 shrink-0" />
        </Link>

        <Button type="submit" disabled={saving} className="bg-blue-600 hover:bg-blue-700" data-testid="save-site-settings">
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save site settings"}
        </Button>
      </form>
    </div>
  );
}
