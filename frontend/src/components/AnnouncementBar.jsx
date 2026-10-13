import React, { useState } from "react";
import { X, Copy, Megaphone, Sparkles, Radio, AlertTriangle, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { useSite } from "../lib/site";
import SmartLink from "./SmartLink";

const KEY = "ann_dismissed";
export const ANN_STYLES = {
  info: { cls: "from-blue-700 to-blue-600", icon: Megaphone },
  offer: { cls: "from-emerald-700 to-teal-600", icon: Sparkles },
  live: { cls: "from-rose-700 to-red-600", icon: Radio },
  warning: { cls: "from-amber-600 to-orange-600", icon: AlertTriangle },
};

export function AnnouncementView({ a, onClose }) {
  const st = ANN_STYLES[a.style] || ANN_STYLES.info;
  const copy = () => navigator.clipboard.writeText(a.coupon_code).then(() => toast.success(`Coupon ${a.coupon_code} copied`));
  return (
    <div className={`relative bg-gradient-to-r ${st.cls} text-white fade-in`} data-testid="announcement-bar" role="region" aria-label="Announcement">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 pr-12 flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-sm">
        <span className="flex items-center gap-2 text-center" data-testid="announcement-message">
          <st.icon className={`w-4 h-4 shrink-0 ${a.style === "live" ? "animate-pulse" : ""}`} />{a.message}
        </span>
        {a.coupon_code && (
          <button type="button" onClick={copy} className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded border border-dashed border-white/60 mono-font text-xs font-semibold hover:bg-white/10 transition-colors" data-testid="announcement-coupon">
            {a.coupon_code} <Copy className="w-3 h-3" />
          </button>
        )}
        {a.cta_label && a.cta_url && (
          <SmartLink to={a.cta_url} className="inline-flex items-center gap-1 font-semibold underline underline-offset-4 hover:no-underline" data-testid="announcement-cta">
            {a.cta_label} <ArrowRight className="w-3.5 h-3.5" />
          </SmartLink>
        )}
      </div>
      {onClose && (
        <button type="button" onClick={onClose} aria-label="Dismiss announcement" className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-white/15 transition-colors" data-testid="announcement-close">
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

export default function AnnouncementBar() {
  const { site } = useSite();
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(KEY));
  const a = site?.announcement;
  if (!a || dismissed === a.version) return null;
  if (a.ends_at && new Date(a.ends_at) <= new Date()) return null;
  if (a.starts_at && new Date(a.starts_at) > new Date()) return null;
  const close = () => { localStorage.setItem(KEY, a.version); setDismissed(a.version); };
  return <AnnouncementView a={a} onClose={close} />;
}
