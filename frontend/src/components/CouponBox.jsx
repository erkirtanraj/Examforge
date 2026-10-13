import React, { useState } from "react";
import { TicketPercent, X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";

export default function CouponBox({ itemType, itemId, applied, onApplied, disabled }) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const apply = async (e) => {
    e.preventDefault();
    if (!code.trim()) return;
    setBusy(true);
    try {
      const { data } = await api.post("/coupons/validate", { item_type: itemType, item_id: itemId, code });
      onApplied(data);
      toast.success(`Coupon ${data.code} applied`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not apply coupon");
    } finally { setBusy(false); }
  };

  if (applied) {
    return (
      <div className="mt-4 flex items-center justify-between rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm" data-testid="coupon-applied">
        <span className="flex items-center gap-2 text-emerald-300"><TicketPercent className="w-4 h-4" /><b className="mono-font">{applied.code}</b> −₹{(applied.discount / 100).toFixed(0)}</span>
        <button onClick={() => { onApplied(null); setCode(""); }} className="text-gray-400 hover:text-white" data-testid="coupon-remove-btn"><X className="w-4 h-4" /></button>
      </div>
    );
  }
  return (
    <form onSubmit={apply} className="mt-4 flex gap-2">
      <input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="Coupon code" disabled={disabled}
             className="flex-1 min-w-0 px-3 py-2 rounded-md bg-[#0b1120] border border-gray-800 text-white text-sm mono-font focus:outline-none focus:border-blue-500" data-testid="coupon-input" />
      <button type="submit" disabled={busy || disabled} className="px-3 rounded-md border border-gray-700 text-sm text-gray-200 hover:bg-gray-800 disabled:opacity-50" data-testid="coupon-apply-btn">
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : "Apply"}
      </button>
    </form>
  );
}
