import React from "react";
import { useLocation } from "react-router-dom";
import { useSite } from "../lib/site";
import SmartLink from "./SmartLink";

export default function Footer() {
  const { site } = useSite();
  const loc = useLocation();
  if (!site || loc.pathname.startsWith("/exam/") || loc.pathname.startsWith("/admin")) return null;
  const { footer, header } = site;
  return (
    <footer className="border-t border-gray-800 mt-10" data-testid="site-footer">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10 text-sm text-gray-500 flex flex-wrap justify-between gap-6">
        <div className="max-w-sm">
          <div className="heading-font text-white font-semibold" data-testid="footer-brand">{header.brand_name}</div>
          {footer.tagline && <p className="mt-1" data-testid="footer-tagline">{footer.tagline}</p>}
          <div className="mt-3" data-testid="footer-copyright">{footer.copyright}</div>
        </div>
        <div className="flex flex-wrap gap-5 items-start">
          {footer.links.map((l, i) => (
            <SmartLink key={i} to={l.url} className="hover:text-gray-300 transition-colors" data-testid={`footer-link-${i}`}>{l.label}</SmartLink>
          ))}
        </div>
      </div>
    </footer>
  );
}
