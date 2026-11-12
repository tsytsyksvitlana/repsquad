import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { exKey } from "../utils/format.js";
import { useAuth } from "./AuthContext.jsx";

const VideosContext = createContext(null);

/** Built-in exercise videos, loaded once after sign-in. Lookups are by normalised exercise name. */
export function VideosProvider({ children }) {
  const { status } = useAuth();
  const [byKey, setByKey] = useState(() => new Map());

  useEffect(() => {
    if (status !== "authed") return;
    let cancelled = false;
    api("GET", "/api/videos")
      .then(({ items }) => { if (!cancelled) setByKey(new Map(items.map((v) => [v.name_key.toLowerCase(), v]))); })
      .catch(() => { /* videos are optional */ });
    return () => { cancelled = true; };
  }, [status]);

  const value = useMemo(() => ({ videoFor: (name) => byKey.get(exKey(name || "")) || null }), [byKey]);
  return <VideosContext.Provider value={value}>{children}</VideosContext.Provider>;
}

export const useVideos = () => useContext(VideosContext);
