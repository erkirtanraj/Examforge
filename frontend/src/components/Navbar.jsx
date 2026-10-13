import React from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Button } from "./ui/button";
import { GraduationCap, LayoutDashboard, LogOut, Shield, Menu, X } from "lucide-react";
import { useState } from "react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [open, setOpen] = useState(false);

  // Hide navbar on exam page
  if (loc.pathname.startsWith("/exam/")) return null;

  const links = [
    { to: "/test-series", label: "Test Series" },
    { to: "/courses", label: "Courses" },
    { to: "/study-materials", label: "Study Materials" },
  ];

  return (
    <header className="glass-nav sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2" data-testid="nav-logo">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-white" />
          </div>
          <span className="heading-font text-xl font-bold text-white">ExamForge</span>
        </Link>

        <nav className="hidden md:flex items-center gap-6">
          {links.map((l) => (
            <Link key={l.to} to={l.to} data-testid={`nav-${l.to.slice(1)}`}
                  className={`text-sm font-medium transition-colors ${loc.pathname.startsWith(l.to) ? "text-cyan-400" : "text-gray-300 hover:text-white"}`}>
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          {user ? (
            <>
              {(user.role === "admin" || user.role === "super_admin") && (
                <Button variant="outline" size="sm" onClick={() => nav("/admin")} data-testid="nav-admin-btn"
                        className="border-gray-700 text-gray-200 hover:bg-gray-800 bg-transparent">
                  <Shield className="w-4 h-4 mr-1" /> Admin
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={() => nav("/dashboard")} data-testid="nav-dashboard-btn"
                      className="border-gray-700 text-gray-200 hover:bg-gray-800 bg-transparent">
                <LayoutDashboard className="w-4 h-4 mr-1" /> Dashboard
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { logout(); nav("/"); }} data-testid="nav-logout-btn"
                      className="text-gray-300 hover:text-white hover:bg-gray-800">
                <LogOut className="w-4 h-4" />
              </Button>
              <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-sm font-semibold text-white">
                {user.name?.[0]?.toUpperCase()}
              </div>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm text-gray-300 hover:text-white" data-testid="nav-login-link">Sign in</Link>
              <Link to="/register" data-testid="nav-register-link">
                <Button size="sm" className="bg-blue-600 hover:bg-blue-700">Get Started</Button>
              </Link>
            </>
          )}
        </div>

        <button className="md:hidden text-white" onClick={() => setOpen(!open)} data-testid="nav-mobile-toggle">
          {open ? <X /> : <Menu />}
        </button>
      </div>

      {open && (
        <div className="md:hidden border-t border-gray-800 bg-[#0b1120] px-4 py-4 space-y-3">
          {links.map((l) => (
            <Link key={l.to} to={l.to} onClick={() => setOpen(false)} className="block text-gray-200">
              {l.label}
            </Link>
          ))}
          {user ? (
            <>
              <Link to="/dashboard" onClick={() => setOpen(false)} className="block text-gray-200">Dashboard</Link>
              {user.role === "admin" && <Link to="/admin" onClick={() => setOpen(false)} className="block text-gray-200">Admin</Link>}
              <button onClick={() => { logout(); nav("/"); setOpen(false); }} className="block text-rose-400">Log out</button>
            </>
          ) : (
            <>
              <Link to="/login" onClick={() => setOpen(false)} className="block text-gray-200">Sign in</Link>
              <Link to="/register" onClick={() => setOpen(false)} className="block text-blue-400">Get Started</Link>
            </>
          )}
        </div>
      )}
    </header>
  );
}
