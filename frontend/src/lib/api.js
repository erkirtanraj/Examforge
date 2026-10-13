import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API_BASE = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("lms_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const { status, data } = err.response || {};
    const detail = typeof data?.detail === "string" ? data.detail : "";
    const forced = (status === 403 && detail.includes("suspended")) || (status === 401 && detail.includes("session has expired"));
    if (forced && localStorage.getItem("lms_token")) {
      localStorage.removeItem("lms_token");
      window.location.assign(`/login?reason=${status === 403 ? "suspended" : "expired"}`);
    }
    return Promise.reject(err);
  }
);

export const assetUrl = (u) => (u && u.startsWith("/api/") ? `${BACKEND_URL}${u}` : u);
