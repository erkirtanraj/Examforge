import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { PageHeader, rupees } from "../../components/admin/kit";
import { Users, FileQuestion, Layers, BookOpen, FileText, PlayCircle, ShoppingBag, IndianRupee, ArrowRight } from "lucide-react";

const Stat = ({ icon: Icon, label, value, testid }) => (
  <div className="card-elev p-4" data-testid={testid}>
    <div className="flex items-center gap-2 text-xs mono-font uppercase tracking-wider text-cyan-300"><Icon className="w-4 h-4" />{label}</div>
    <div className="text-2xl font-bold text-white mt-2">{value ?? "—"}</div>
  </div>
);

const QUICK = [
  { to: "/admin/questions", label: "Add questions to the bank" },
  { to: "/admin/tests", label: "Build a new mock test" },
  { to: "/admin/courses", label: "Create a course with lessons" },
];

export default function Overview() {
  const [s, setS] = useState(null);
  useEffect(() => { api.get("/admin/stats").then((r) => setS(r.data)); }, []);

  return (
    <div>
      <PageHeader eyebrow="Admin Panel" title="Platform overview" desc="Live counts across content, learners and sales." />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat icon={Users} label="Users" value={s?.users} testid="admin-stat-users" />
        <Stat icon={FileQuestion} label="Questions" value={s?.questions} testid="admin-stat-questions" />
        <Stat icon={Layers} label="Test Series" value={s?.test_series} testid="admin-stat-series" />
        <Stat icon={PlayCircle} label="Tests" value={s?.tests} testid="admin-stat-tests" />
        <Stat icon={BookOpen} label="Courses" value={s?.courses} testid="admin-stat-courses" />
        <Stat icon={FileText} label="Attempts" value={s?.attempts} testid="admin-stat-attempts" />
        {s && "orders_paid" in s && <Stat icon={ShoppingBag} label="Paid Orders" value={s.orders_paid} testid="admin-stat-orders" />}
        {s && "revenue" in s && <Stat icon={IndianRupee} label="Revenue" value={rupees(s.revenue)} testid="admin-stat-revenue" />}
      </div>
      <h2 className="heading-font text-lg font-semibold text-white mt-10 mb-3">Quick actions</h2>
      <div className="grid md:grid-cols-3 gap-4">
        {QUICK.map((q) => (
          <Link key={q.to} to={q.to} className="card-elev p-4 flex items-center justify-between text-sm text-gray-200 hover:border-blue-500/40">
            {q.label} <ArrowRight className="w-4 h-4 text-cyan-300" />
          </Link>
        ))}
      </div>
    </div>
  );
}
