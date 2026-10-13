import React from "react";
import { GraduationCap } from "lucide-react";
import { useSite } from "../lib/site";
import { assetUrl } from "../lib/api";

export default function BrandLogo({ small = false }) {
  const { site } = useSite();
  const h = site?.header;
  const box = small ? "w-8 h-8" : "w-9 h-9";
  return (
    <>
      {h?.logo_url ? (
        <img src={assetUrl(h.logo_url)} alt={h.brand_name} className={`${small ? "h-8" : "h-9"} max-w-[160px] w-auto object-contain`} data-testid="brand-logo-img" />
      ) : (
        <div className={`${box} rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center shrink-0`}>
          <GraduationCap className={`${small ? "w-4 h-4" : "w-5 h-5"} text-white`} />
        </div>
      )}
      {(h?.show_brand_name ?? true) && (
        <span className={`heading-font font-bold text-white truncate ${small ? "" : "text-xl"}`} data-testid="nav-brand-name">{h?.brand_name}</span>
      )}
    </>
  );
}
