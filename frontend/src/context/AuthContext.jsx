import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, onUnauthorized, readToken, writeToken } from "../api.js";

const AuthContext = createContext(null);

/** Holds the session: status is "loading" | "anon" | "authed". */
export function AuthProvider({ children }) {
  const [token, setToken] = useState(readToken);
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(Boolean(readToken()));

  const clear = useCallback(() => {
    writeToken(null);
    setToken(null);
    setMe(null);
  }, []);

  useEffect(() => onUnauthorized(clear), [clear]);

  // Restore the profile for a stored token.
  useEffect(() => {
    if (!token || me) { setLoading(false); return; }
    let cancelled = false;
    api("GET", "/api/me")
      .then((profile) => { if (!cancelled) setMe(profile); })
      .catch(() => { if (!cancelled) clear(); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [token, me, clear]);

  const start = useCallback((result) => {
    writeToken(result.token);
    setToken(result.token);
    setMe(result.user);
  }, []);

  const login = useCallback(async (username, password) => start(await api("POST", "/api/auth/login", { username, password })), [start]);
  const register = useCallback(async (username, password, displayName) =>
    start(await api("POST", "/api/auth/register", { username, password, display_name: displayName })), [start]);
  const logout = useCallback(async () => {
    try { await api("POST", "/api/auth/logout", {}); } catch { /* ignore: the local session is dropped anyway */ }
    clear();
  }, [clear]);

  const status = loading ? "loading" : token && me ? "authed" : "anon";
  const value = useMemo(() => ({ status, me, setMe, login, register, logout }), [status, me, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
