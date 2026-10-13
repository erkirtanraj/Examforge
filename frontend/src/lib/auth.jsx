import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

const AuthCtx = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Returning from Google OAuth: AuthCallback exchanges session_id first
    if (window.location.hash?.includes("session_id=")) { setLoading(false); return; }
    const t = localStorage.getItem("lms_token");
    if (!t) { setLoading(false); return; }
    api.get("/auth/me").then((r) => setUser(r.data)).catch(() => {
      localStorage.removeItem("lms_token");
    }).finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("lms_token", data.token);
    setUser(data.user);
    return data.user;
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    localStorage.setItem("lms_token", data.token);
    setUser(data.user);
    return data.user;
  };

  const loginWithToken = (token, u) => {
    localStorage.setItem("lms_token", token);
    setUser(u);
  };

  const logout = () => {
    localStorage.removeItem("lms_token");
    setUser(null);
  };

  return <AuthCtx.Provider value={{ user, loading, login, register, loginWithToken, logout }}>{children}</AuthCtx.Provider>;
};

export const useAuth = () => useContext(AuthCtx);
