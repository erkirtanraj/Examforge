import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, assetUrl } from "./api";

const KEY = "site_cache_v1";
const cached = () => { try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; } };

function setFavicon(url) {
  let link = document.querySelector("link[rel='icon']");
  if (!link) { link = document.createElement("link"); link.rel = "icon"; document.head.appendChild(link); }
  link.href = assetUrl(url) || "/favicon.ico";
}

const SiteCtx = createContext({ site: null, reload: () => {} });

export function SiteProvider({ children }) {
  const [site, setSite] = useState(cached);
  const reload = useCallback(() => api.get("/site").then((r) => { setSite(r.data); localStorage.setItem(KEY, JSON.stringify(r.data)); }).catch(() => {}), []);
  useEffect(() => { reload(); }, [reload]);
  useEffect(() => {
    if (!site?.header) return;
    document.title = site.header.brand_name;
    setFavicon(site.header.favicon_url);
  }, [site]);
  return <SiteCtx.Provider value={{ site, reload }}>{children}</SiteCtx.Provider>;
}

export const useSite = () => useContext(SiteCtx);
