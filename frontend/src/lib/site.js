import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api";

const SiteCtx = createContext({ site: null, reload: () => {} });

export function SiteProvider({ children }) {
  const [site, setSite] = useState(null);
  const reload = useCallback(() => api.get("/site").then((r) => setSite(r.data)).catch(() => {}), []);
  useEffect(() => { reload(); }, [reload]);
  useEffect(() => { if (site?.header?.brand_name) document.title = site.header.brand_name; }, [site]);
  return <SiteCtx.Provider value={{ site, reload }}>{children}</SiteCtx.Provider>;
}

export const useSite = () => useContext(SiteCtx);
