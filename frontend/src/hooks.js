import { useCallback, useEffect, useState } from "react";
import { useToast } from "./context/ToastContext.jsx";

/** Runs an async function when deps change and tracks { data, error, loading }; stale results are ignored. */
export function useAsync(fn, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    fn()
      .then((data) => { if (!cancelled) setState({ data, error: null, loading: false }); })
      .catch((e) => { if (!cancelled) setState({ data: null, error: e.message, loading: false }); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

/** Sets document.title for the current page. */
export function useTitle(title) {
  useEffect(() => { document.title = title; }, [title]);
}

/** A counter that makes a page or list reload: put `version` into the deps/reset key and call `refresh()`. */
export function useRefresh() {
  const [version, setVersion] = useState(0);
  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  return [version, refresh];
}

/**
 * Returns `run(fn, successMessage?)` for user actions: it awaits fn, shows the success toast and
 * resolves to true, or shows the error as a toast and resolves to false.
 */
export function useAction() {
  const toast = useToast();
  return useCallback(async (fn, successMessage) => {
    try {
      await fn();
      if (successMessage) toast(successMessage);
      return true;
    } catch (e) {
      toast(e.message, "err");
      return false;
    }
  }, [toast]);
}
