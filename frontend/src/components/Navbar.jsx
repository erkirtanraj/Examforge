import React from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useSite } from "../lib/site";
import SmartLink from "./SmartLink";
import BrandLogo from "./BrandLogo";
import { Button } from "./ui/button";
import { LayoutDashboard, LogOut, Shield, Menu, X } from "lucide-react";
import { useState } from "react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const { site } = useSite();

  // Hide navbar on exam page
  if (loc.pathname.startsWith("/exam/") || loc.pathname.startsWith("/admin")) return null;

  const header = site?.header;
  const links = (header?.nav_links || []).map((l) => ({ to: l.url, label: l.label }));

  return (
    <header className="glass-nav sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 min-w-0" data-testid="nav-logo">
          <BrandLogo />
        </Link>

        <nav className="hidden md:flex items-center gap-6">
          {links.map((l) => (
            <SmartLink key={l.to + l.label} to={l.to} data-testid={`nav-${l.to.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "")}`}
                  className={`text-sm font-medium transition-colors ${l.to !== "/" && loc.pathname.startsWith(l.to) ? "text-cyan-400" : "text-gray-300 hover:text-white"}`}>
              {l.label}
            </SmartLink>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          {user ? (
            <>
              {["admin", "super_admin", "teacher"].includes(user.role) && (
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
              <SmartLink to={header?.cta_url || "/register"} data-testid="nav-register-link">
                <Button size="sm" className="bg-blue-600 hover:bg-blue-700">{header?.cta_label || "Get Started"}</Button>
              </SmartLink>
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
            <SmartLink key={l.to + l.label} to={l.to} onClick={() => setOpen(false)} className="block text-gray-200">
              {l.label}
            </SmartLink>
          ))}
          {user ? (
            <>
              <Link to="/dashboard" onClick={() => setOpen(false)} className="block text-gray-200">Dashboard</Link>
              {["admin", "super_admin", "teacher"].includes(user.role) && <Link to="/admin" onClick={() => setOpen(false)} className="block text-gray-200">Admin</Link>}
              <button onClick={() => { logout(); nav("/"); setOpen(false); }} className="block text-rose-400">Log out</button>
            </>
          ) : (
            <>
              <Link to="/login" onClick={() => setOpen(false)} className="block text-gray-200">Sign in</Link>
              <SmartLink to={header?.cta_url || "/register"} onClick={() => setOpen(false)} className="block text-blue-400">{header?.cta_label || "Get Started"}</SmartLink>
            </>
          )}
        </div>
      )}
    </header>
  );
}
