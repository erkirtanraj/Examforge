import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import LiveMockBanner from "../components/LiveMockBanner";
import SmartLink from "../components/SmartLink";
import { useSite } from "../lib/site";
import { FEATURE_ICONS } from "../lib/featureIcons";
import { Clock, Zap, GraduationCap, ArrowRight, FileText, Scale, Landmark, Train, Atom, CheckCircle2, Target } from "lucide-react";

const ICONS = { FileText, Scale, Landmark, Train, Atom, GraduationCap };

export default function Home() {
  const [categories, setCategories] = useState([]);
  const [featured, setFeatured] = useState([]);
  const { site } = useSite();
  const hero = site?.hero;

  useEffect(() => {
    api.get("/categories").then((r) => setCategories(r.data));
    api.get("/test-series").then((r) => setFeatured(r.data.slice(0, 4)));
  }, []);

  return (
    <div className="app-shell">
      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 grid-mesh opacity-30" />
        <div className="absolute top-10 left-10 w-72 h-72 rounded-full bg-blue-600/20 blur-3xl" />
        <div className="absolute bottom-20 right-10 w-96 h-96 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-20 lg:py-28 grid lg:grid-cols-2 gap-12 items-center">
          <div className="fade-in">
            {hero?.badge_text && (
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 text-xs font-medium mono-font" data-testid="hero-badge">
                <Zap className="w-3.5 h-3.5" /> {hero.badge_text}
              </div>
            )}
            <h1 className="heading-font mt-5 text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white leading-tight" data-testid="hero-title">
              {hero?.title} {hero?.highlight && <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-300">{hero.highlight}</span>}
            </h1>
            <p className="mt-5 text-base sm:text-lg text-gray-300 max-w-xl" data-testid="hero-subtitle">{hero?.subtitle}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              {hero?.primary_cta_label && (
                <SmartLink to={hero.primary_cta_url} data-testid="hero-start-cta">
                  <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white h-12 px-6">
                    {hero.primary_cta_label} <ArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </SmartLink>
              )}
              {hero?.secondary_cta_label && (
                <SmartLink to={hero.secondary_cta_url} data-testid="hero-register-cta">
                  <Button size="lg" variant="outline" className="h-12 px-6 border-gray-700 bg-transparent text-white hover:bg-gray-800">
                    {hero.secondary_cta_label}
                  </Button>
                </SmartLink>
              )}
            </div>
            <div className="mt-10 grid grid-cols-3 gap-6 max-w-md" data-testid="hero-stats">
              {(site?.stats || []).filter((s) => s.display).map((s, i) => (
                <div key={i} data-testid={`hero-stat-${i}`}>
                  <div className="heading-font text-2xl font-bold text-white">{s.display}</div>
                  <div className="text-xs text-gray-400 mono-font uppercase tracking-wider">{s.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Mock exam preview card */}
          <div className="relative fade-in">
            <div className="card-elev p-6 relative">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-xs text-gray-400 mono-font uppercase">SSC CGL · Tier I</div>
                  <div className="heading-font text-lg font-semibold text-white">Full Mock Test · Section A</div>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-300 mono-font text-sm">
                  <Clock className="w-4 h-4" /> 00:48:12
                </div>
              </div>
              <div className="rounded-lg bg-[#0b1120] p-4 border border-gray-800">
                <div className="text-xs text-gray-400 mono-font mb-2">Q.14 · Quantitative Aptitude</div>
                <div className="text-white text-sm mb-4">If a train travels 60 km in 1.5 hours, what is its speed?</div>
                <div className="space-y-2">
                  {["35 km/h", "40 km/h", "45 km/h", "50 km/h"].map((o, i) => (
                    <div key={o} className={`p-2.5 rounded-md border text-sm ${i === 1 ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-300" : "border-gray-800 text-gray-300"}`}>
                      <span className="mono-font mr-2">{String.fromCharCode(65 + i)}.</span>{o}
                      {i === 1 && <CheckCircle2 className="w-4 h-4 inline float-right text-emerald-400" />}
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-4 grid grid-cols-5 gap-1.5">
                {[...Array(20)].map((_, i) => {
                  const cls = i < 8 ? "qp-answered" : i === 13 ? "qp-current qp-not-visited" : i < 12 ? "qp-not-answered" : i < 14 ? "qp-marked" : "qp-not-visited";
                  return <div key={i} className={`${cls} h-7 rounded flex items-center justify-center text-xs mono-font font-semibold`}>{i + 1}</div>;
                })}
              </div>
              <div className="mt-3 flex flex-wrap gap-3 text-xs mono-font">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm qp-answered inline-block"/>Answered</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm qp-not-answered inline-block"/>Not Answered</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm qp-marked inline-block"/>Marked</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <LiveMockBanner />

      {/* Categories */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="flex items-end justify-between mb-8">
          <div>
            <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mb-2">Exam Categories</div>
            <h2 className="heading-font text-3xl font-bold text-white">Choose your target exam</h2>
          </div>
          <Link to="/test-series" className="text-sm text-blue-400 hover:text-blue-300 hidden sm:inline">View all →</Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {categories.map((c) => {
            const Icon = ICONS[c.icon] || GraduationCap;
            return (
              <Link key={c.id} to={`/test-series?category=${c.id}`} data-testid={`category-${c.slug}`}
                    className="card-elev p-5 hover:border-blue-500/40 group">
                <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-blue-600/30 to-cyan-500/20 border border-blue-500/30 flex items-center justify-center mb-3">
                  <Icon className="w-5 h-5 text-cyan-300" />
                </div>
                <div className="heading-font text-base font-semibold text-white group-hover:text-cyan-300 transition-colors">{c.name}</div>
                <div className="text-xs text-gray-400 mt-1 line-clamp-2">{c.description}</div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Featured series */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex items-end justify-between mb-8">
          <div>
            <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mb-2">Featured</div>
            <h2 className="heading-font text-3xl font-bold text-white">Top test series this week</h2>
          </div>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
          {featured.map((s) => (
            <Link key={s.id} to={`/test-series/${s.id}`} data-testid={`featured-series-${s.id}`} className="card-elev overflow-hidden hover:border-blue-500/40">
              <div className="aspect-video overflow-hidden bg-gray-800">
                {s.thumbnail && <img src={s.thumbnail} alt="" className="w-full h-full object-cover" />}
              </div>
              <div className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  {s.is_free ? (
                    <span className="text-xs mono-font px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">FREE</span>
                  ) : (
                    <span className="text-xs mono-font px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">PREMIUM</span>
                  )}
                  <span className="text-xs text-gray-400 mono-font">{s.tests_count || 0} TESTS</span>
                </div>
                <div className="heading-font text-sm font-semibold text-white line-clamp-2">{s.title}</div>
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-xs text-gray-400">{s.language?.toUpperCase()}</span>
                  <span className="text-sm font-bold text-cyan-300">
                    {s.is_free ? "Start" : `₹${(s.price / 100).toFixed(0)}`}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="grid md:grid-cols-3 gap-6" data-testid="home-features">
          {(site?.features || []).map((f, i) => {
            const Icon = FEATURE_ICONS[f.icon] || Target;
            return (
            <div key={i} className="card-elev p-6" data-testid={`home-feature-${i}`}>
              <Icon className={`w-7 h-7 mb-3 ${["text-blue-400", "text-cyan-400", "text-emerald-400"][i % 3]}`} />
              <h3 className="heading-font text-lg font-semibold text-white">{f.title}</h3>
              <p className="text-sm text-gray-400 mt-2">{f.desc}</p>
            </div>
            );
          })}
        </div>
      </section>

    </div>
  );
}
