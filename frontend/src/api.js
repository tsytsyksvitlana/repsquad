// Thin fetch wrapper around the JSON API. The session token lives in localStorage.
const TOKEN_KEY = "repsquad.token";

export function readToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } // storage may be unavailable
}

export function writeToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token); else localStorage.removeItem(TOKEN_KEY);
  } catch { /* storage unavailable */ }
}

let unauthorizedHandler = () => {};
/** The auth provider registers a callback that runs when the server rejects the session. */
export const onUnauthorized = (fn) => { unauthorizedHandler = fn; };

export async function api(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  const token = readToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  let data = null;
  try { data = await res.json(); } catch { /* empty response */ }
  if (res.status === 401 && token && !path.startsWith("/api/auth/")) {
    unauthorizedHandler();
    throw new Error("Сесія завершилась. Увійдіть знову.");
  }
  if (!res.ok) throw new Error((data && data.error) || `Помилка ${res.status}`);
  return data;
}
