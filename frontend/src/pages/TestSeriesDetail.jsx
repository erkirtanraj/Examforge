import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, assetUrl } from "../lib/api";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { useAuth } from "../lib/auth";
import { useSite } from "../lib/site";
import { Clock, FileText, Lock, Play, ShieldCheck, Trophy, Layers } from "lucide-react";
import { toast } from "sonner";
import CouponBox from "../components/CouponBox";
import TestStartButton from "../components/TestStartButton";
import { fmtDateTime } from "../components/Countdown";

export default function TestSeriesDetail() {
  const { site } = useSite();
  const { id } = useParams();
  const [series, setSeries] = useState(null);
  const [entitlements, setEntitlements] = useState([]);
  const { user } = useAuth();
  const nav = useNavigate();
  const [buying, setBuying] = useState(false);
  const [coupon, setCoupon] = useState(null);

  useEffect(() => {
    api.get(`/test-series/${id}`).then((r) => setSeries(r.data));
    if (user) api.get("/my/entitlements").then((r) => setEntitlements(r.data));
  }, [id, user]);

  const hasAccess = series?.is_free || entitlements.some((e) => e.item_type === "test_series" && e.item_id === id)
    || user?.role === "admin" || user?.role === "super_admin";

  const startTest = async (testId) => {
    if (!user) { nav("/login"); return; }
    if (!hasAccess) { toast.error("Please purchase this series to attempt tests."); return; }
    try {
      const { data } = await api.post(`/tests/${testId}/start`);
      nav(`/exam/${data.id}`);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not start test");
    }
  };

  const buy = async () => {
    if (!user) { nav("/login"); return; }
    setBuying(true);
    try {
      const { data } = await api.post("/orders", { item_type: "test_series", item_id: id, coupon_code: coupon?.code || null });
      if (data.status === "paid") {
        toast.success("Enrolled successfully");
        const r = await api.get("/my/entitlements");
        setEntitlements(r.data);
      } else if (data.demo_mode) {
        toast.info("Razorpay keys not configured. Add RAZORPAY_KEY_ID/SECRET to backend/.env to enable live payments.");
      } else {
        // Open Razorpay checkout
        const options = {
          key: data.razorpay_key,
          amount: data.amount,
          currency: data.currency,
          order_id: data.razorpay_order_id,
          name: "ExamForge",
          description: series.title,
          handler: async (resp) => {
            await api.post("/orders/verify", { ...resp, order_id: data.id });
            toast.success("Payment successful");
            const r = await api.get("/my/entitlements");
            setEntitlements(r.data);
          },
          prefill: { email: user.email, name: user.name },
          theme: { color: site?.theme?.primary || "#2563EB" },
        };
        const rzp = new window.Razorpay(options);
        rzp.open();
      }
    } catch (e) {
      toast.error(e.response?.data?.detail || "Checkout failed");
    } finally {
      setBuying(false);
    }
  };

  if (!series) return <div className="max-w-7xl mx-auto px-4 py-16 text-gray-400">Loading…</div>;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 min-w-0">
          <div className="aspect-video rounded-xl overflow-hidden bg-gray-800 border border-gray-800 mb-6">
            {series.thumbnail && <img loading="lazy" decoding="async" src={assetUrl(series.thumbnail)} alt="" className="w-full h-full object-cover" />}
          </div>
          <div className="flex items-center gap-2 mb-3">
            {series.is_free
              ? <Badge className="bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">FREE SERIES</Badge>
              : <Badge className="bg-amber-500/10 text-amber-300 border border-amber-500/30">PREMIUM</Badge>}
            <span className="text-xs text-gray-400 mono-font">{series.tests?.length || 0} TESTS · {series.language?.toUpperCase()}</span>
          </div>
          <h1 className="heading-font text-3xl sm:text-4xl font-bold text-white" data-testid="series-title">{series.title}</h1>
          <p className="text-gray-400 mt-4">{series.description}</p>

          <h2 className="heading-font text-xl font-semibold text-white mt-10 mb-4">Included tests</h2>
          <div className="space-y-3">
            {series.tests?.map((t, i) => (
              <div key={t.id} className="card-elev p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-xs text-gray-400 mono-font">TEST #{i + 1}</div>
                  <div className="text-white font-medium">{t.title}</div>
                  <div className="text-xs text-gray-500 flex flex-wrap gap-x-4 gap-y-1 mt-1">
                    <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {t.duration_minutes} min</span>
                    {t.live_start_at && <span className="flex items-center gap-1 text-rose-300 mono-font" data-testid={`live-badge-${t.id}`}>● LIVE {fmtDateTime(t.live_start_at)}</span>}
                    {t.sections?.length > 1 && <span className="flex items-center gap-1" data-testid={`test-sections-${t.id}`}><Layers className="w-3 h-3" /> {t.sections.map((s) => s.name).join(" · ")}{t.sectional_timing ? " (timed)" : ""}</span>}
                    <Link to={`/leaderboard/${t.id}`} className="flex items-center gap-1 text-amber-300 hover:text-amber-200" data-testid={`leaderboard-link-${t.id}`}><Trophy className="w-3 h-3" /> Leaderboard</Link>
                    <span className="flex items-center gap-1"><FileText className="w-3 h-3" /> {t.total_marks} marks</span>
                  </div>
                </div>
                <TestStartButton t={t} hasAccess={hasAccess} onStart={() => startTest(t.id)} />
              </div>
            ))}
          </div>
        </div>

        <aside>
          <div className="card-elev p-6 lg:sticky lg:top-24">
            <div className="heading-font text-3xl font-bold text-white" data-testid="series-price">
              {series.is_free ? "Free" : coupon ? (
                <span className="flex items-baseline gap-3">₹{(coupon.final_amount / 100).toFixed(0)}{" "}
                  <span className="text-lg text-gray-500 line-through font-normal" aria-label="original price" data-testid="series-original-price">₹{(series.price / 100).toFixed(0)}</span>
                </span>
              ) : `₹${(series.price / 100).toFixed(0)}`}
            </div>
            <div className="text-xs text-gray-400 mono-font uppercase mt-1">
              {series.validity_days} days validity
            </div>
            {!series.is_free && !hasAccess && user && <CouponBox itemType="test_series" itemId={id} applied={coupon} onApplied={setCoupon} />}
            <Button onClick={hasAccess ? () => startTest(series.tests?.[0]?.id) : buy} disabled={buying}
                    data-testid="series-buy-btn" className="w-full mt-5 bg-blue-600 hover:bg-blue-700 h-11">
              {hasAccess ? "Start Learning" : (buying ? "Processing…" : (series.is_free ? "Enroll Free" : "Buy Now"))}
            </Button>
            <div className="mt-5 text-xs text-gray-400 space-y-2">
              <div className="flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-400" /> Server-authoritative timer</div>
              <div className="flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-400" /> Autosave every answer</div>
              <div className="flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-400" /> Instant result + analytics</div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
