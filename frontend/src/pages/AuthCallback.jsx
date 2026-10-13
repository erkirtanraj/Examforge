import React, { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function AuthCallback() {
  const loc = useLocation();
  const nav = useNavigate();
  const { loginWithToken } = useAuth();
  const done = useRef(false);

  useEffect(() => {
    if (done.current) return;
    done.current = true;
    const sessionId = new URLSearchParams(loc.hash.slice(1)).get("session_id");
    api.post("/auth/google", { session_id: sessionId })
      .then(({ data }) => {
        loginWithToken(data.token, data.user);
        toast.success(`Welcome, ${data.user.name}`);
        const staff = ["admin", "super_admin", "teacher"].includes(data.user.role);
        nav(staff ? "/admin" : "/dashboard", { replace: true });
      })
      .catch(() => {
        toast.error("Google sign-in failed. Please try again.");
        nav("/login", { replace: true });
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div className="min-h-screen flex items-center justify-center text-gray-400 text-sm" data-testid="auth-callback">Signing you in…</div>;
}
