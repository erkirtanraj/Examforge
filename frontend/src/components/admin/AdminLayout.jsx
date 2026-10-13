import React, { useState } from "react";
import { NavLink, Outlet, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../lib/auth";
import { useSite } from "../../lib/site";
import {
  LayoutDashboard, FileQuestion, Layers, PlayCircle, BookOpen, FileText, Tags, Users,
  ShoppingBag, Settings, GraduationCap, LogOut, ExternalLink, Menu, X, Ticket, PanelTop, Home, ScrollText,
} from "lucide-react";

const MENU = [
  { group: "Overview", items: [{ to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true }] },
  {
    group: "Content",
    items: [
      { to: "/admin/questions", label: "Question Bank", icon: FileQuestion },
      { to: "/admin/series", label: "Test Series", icon: Layers },
      { to: "/admin/tests", label: "Tests", icon: PlayCircle },
      { to: "/admin/courses", label: "Courses", icon: BookOpen },
      { to: "/admin/materials", label: "Study Materials", icon: FileText },
      { to: "/admin/categories", label: "Categories", icon: Tags, adminOnly: true },
    ],
  },
  {
    group: "Management",
    adminOnly: true,
    items: [
      { to: "/admin/users", label: "Users", icon: Users },
      { to: "/admin/orders", label: "Orders", icon: ShoppingBag },
      { to: "/admin/coupons", label: "Coupons", icon: Ticket },
    ],
  },
  {
    group: "Settings",
    adminOnly: true,
    items: [
      { to: "/admin/site", label: "Site Settings", icon: PanelTop },
      { to: "/admin/home", label: "Home Page", icon: Home },
      { to: "/admin/pages", label: "Legal Pages", icon: ScrollText },
      { to: "/admin/settings", label: "Payment Settings", icon: Settings },
    ],
  },
];

const Sidebar = ({ isAdmin, onNavigate }) => (
  <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
    {MENU.filter((g) => isAdmin || !g.adminOnly).map((g) => (
      <div key={g.group}>
        <div className="px-3 mb-2 text-[10px] text-gray-500 mono-font uppercase tracking-[0.18em]">{g.group}</div>
        <div className="space-y-0.5">
          {g.items.filter((i) => isAdmin || !i.adminOnly).map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end} onClick={onNavigate}
                     data-testid={`sidebar-${i.label.toLowerCase().replace(/\s+/g, "-")}`}
                     className={({ isActive }) =>
                       `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                         isActive ? "bg-blue-600/15 text-white border-l-2 border-cyan-400" : "text-gray-400 hover:text-white hover:bg-gray-800/60"
                       }`}>
              <i.icon className="w-4 h-4 shrink-0" />
              {i.label}
            </NavLink>
          ))}
        </div>
      </div>
    ))}
  </nav>
);

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const { site } = useSite();
  const isAdmin = ["admin", "super_admin"].includes(user?.role);

  const shell = (
    <>
      <Link to="/" className="flex items-center gap-2 px-5 h-16 border-b border-gray-800 shrink-0" data-testid="admin-brand">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center">
          <GraduationCap className="w-4 h-4 text-white" />
        </div>
        <span className="heading-font font-bold text-white">{site?.header?.brand_name}</span>
        <span className="ml-auto text-[10px] mono-font text-cyan-300 border border-cyan-500/30 rounded px-1.5 py-0.5">
          {isAdmin ? "ADMIN" : "TEACHER"}
        </span>
      </Link>
      <Sidebar isAdmin={isAdmin} onNavigate={() => setOpen(false)} />
      <div className="border-t border-gray-800 p-3 space-y-1 shrink-0">
        <Link to="/" className="flex items-center gap-3 px-3 py-2 rounded-md text-sm text-gray-400 hover:text-white hover:bg-gray-800/60 transition-colors" data-testid="admin-view-site">
          <ExternalLink className="w-4 h-4" /> View site
        </Link>
        <button onClick={() => { logout(); nav("/"); }} data-testid="admin-logout"
                className="w-full flex items-center gap-3 px-3 py-2 rounded-md text-sm text-gray-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors">
          <LogOut className="w-4 h-4" /> Log out
        </button>
        <div className="flex items-center gap-3 px-3 pt-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-xs font-semibold text-white">
            {user?.name?.[0]?.toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="text-sm text-white truncate">{user?.name}</div>
            <div className="text-[11px] text-gray-500 truncate">{user?.email}</div>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <div className="min-h-screen flex">
      <aside className="hidden lg:flex flex-col w-64 fixed inset-y-0 left-0 bg-[#0b1120] border-r border-gray-800 z-30">{shell}</aside>
      {open && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <aside className="relative flex flex-col w-72 bg-[#0b1120] border-r border-gray-800">{shell}</aside>
        </div>
      )}
      <div className="flex-1 lg:ml-64 min-w-0">
        <div className="lg:hidden glass-nav sticky top-0 z-20 h-14 flex items-center px-4 gap-3">
          <button onClick={() => setOpen(true)} data-testid="admin-mobile-menu" className="text-white">
            {open ? <X /> : <Menu />}
          </button>
          <span className="heading-font font-semibold text-white">Admin Panel</span>
        </div>
        <main className="px-4 sm:px-8 py-8 max-w-7xl"><Outlet /></main>
      </div>
    </div>
  );
}
