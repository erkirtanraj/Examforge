import React, { useEffect, useState } from "react";
import { api } from "../lib/api";
import { Users, FileQuestion, Layers, BookOpen, FileText, PlayCircle, ShoppingBag, IndianRupee } from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [orders, setOrders] = useState([]);

  useEffect(() => {
    api.get("/admin/stats").then((r) => setStats(r.data));
    api.get("/admin/users").then((r) => setUsers(r.data));
    api.get("/admin/orders").then((r) => setOrders(r.data));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
      <div className="fade-in">
        <div className="text-xs text-cyan-300 mono-font uppercase tracking-wider mb-2">Admin Panel</div>
        <h1 className="heading-font text-3xl font-bold text-white">Platform overview</h1>
      </div>

      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4">
        <AdminStat icon={<Users className="w-5 h-5" />} label="Users" value={stats?.users} testid="admin-stat-users" />
        <AdminStat icon={<FileQuestion className="w-5 h-5" />} label="Questions" value={stats?.questions} testid="admin-stat-questions" />
        <AdminStat icon={<Layers className="w-5 h-5" />} label="Test Series" value={stats?.test_series} testid="admin-stat-series" />
        <AdminStat icon={<PlayCircle className="w-5 h-5" />} label="Tests" value={stats?.tests} testid="admin-stat-tests" />
        <AdminStat icon={<BookOpen className="w-5 h-5" />} label="Courses" value={stats?.courses} testid="admin-stat-courses" />
        <AdminStat icon={<FileText className="w-5 h-5" />} label="Attempts" value={stats?.attempts} testid="admin-stat-attempts" />
        <AdminStat icon={<ShoppingBag className="w-5 h-5" />} label="Paid Orders" value={stats?.orders_paid} testid="admin-stat-orders" />
        <AdminStat icon={<IndianRupee className="w-5 h-5" />} label="Revenue" value={stats ? `₹${(stats.revenue / 100).toFixed(0)}` : "—"} testid="admin-stat-revenue" />
      </div>

      <div className="mt-10">
        <Tabs defaultValue="users">
          <TabsList className="bg-gray-900 border border-gray-800">
            <TabsTrigger value="users" data-testid="admin-tab-users" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Users</TabsTrigger>
            <TabsTrigger value="orders" data-testid="admin-tab-orders" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">Orders</TabsTrigger>
          </TabsList>
          <TabsContent value="users">
            <div className="card-elev mt-4 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-900/60">
                  <tr className="text-left text-gray-400 mono-font text-xs uppercase">
                    <th className="p-3">Name</th><th className="p-3">Email</th><th className="p-3">Role</th><th className="p-3">Joined</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-t border-gray-800">
                      <td className="p-3 text-white">{u.name}</td>
                      <td className="p-3 text-gray-300">{u.email}</td>
                      <td className="p-3"><span className="text-xs mono-font px-2 py-0.5 rounded border border-blue-500/30 bg-blue-500/10 text-blue-300">{u.role.toUpperCase()}</span></td>
                      <td className="p-3 text-gray-400">{new Date(u.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>
          <TabsContent value="orders">
            <div className="card-elev mt-4 overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-gray-900/60">
                  <tr className="text-left text-gray-400 mono-font text-xs uppercase">
                    <th className="p-3">Item</th><th className="p-3">Amount</th><th className="p-3">Status</th><th className="p-3">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((o) => (
                    <tr key={o.id} className="border-t border-gray-800">
                      <td className="p-3 text-white">{o.item_title || o.item_type}</td>
                      <td className="p-3 text-gray-300 mono-font">₹{(o.amount / 100).toFixed(0)}</td>
                      <td className="p-3">
                        <span className={`text-xs mono-font px-2 py-0.5 rounded border
                          ${o.status === "paid" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-amber-500/40 bg-amber-500/10 text-amber-300"}`}>
                          {o.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="p-3 text-gray-400">{new Date(o.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                  {orders.length === 0 && <tr><td colSpan={4} className="p-6 text-center text-gray-500">No orders yet.</td></tr>}
                </tbody>
              </table>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

const AdminStat = ({ icon, label, value, testid }) => (
  <div className="card-elev p-4" data-testid={testid}>
    <div className="flex items-center gap-2 text-xs mono-font uppercase tracking-wider text-cyan-300">{icon}{label}</div>
    <div className="text-2xl font-bold text-white mt-2">{value ?? "—"}</div>
  </div>
);
