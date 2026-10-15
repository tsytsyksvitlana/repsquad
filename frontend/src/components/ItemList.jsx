import { useCallback, useEffect, useState } from "react";
import { useToast } from "../context/ToastContext.jsx";
import { ErrorBox, Loading } from "./common.jsx";
import { PostCard } from "./PostCard.jsx";
import { WorkoutCard } from "./WorkoutCard.jsx";

/**
 * Paged list of workouts and posts. `fetchPage(offset)` must resolve to { items, has_more }.
 * The list restarts when `resetKey` changes or when a card reports a change (then `onItemsChanged` is called too).
 */
export default function ItemList({ fetchPage, empty, resetKey, onItemsChanged }) {
  const toast = useToast();
  const [state, setState] = useState({ items: [], hasMore: false, loading: true, error: null });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState({ items: [], hasMore: false, loading: true, error: null });
    fetchPage(0)
      .then((page) => { if (!cancelled) setState({ items: page.items, hasMore: page.has_more, loading: false, error: null }); })
      .catch((e) => { if (!cancelled) setState({ items: [], hasMore: false, loading: false, error: e.message }); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey, version]);

  const loadMore = useCallback(async () => {
    try {
      const page = await fetchPage(state.items.length);
      setState((s) => ({ ...s, items: [...s.items, ...page.items], hasMore: page.has_more }));
    } catch (e) { toast(e.message, "err"); }
  }, [fetchPage, state.items.length, toast]);

  const changed = () => { setVersion((v) => v + 1); if (onItemsChanged) onItemsChanged(); };

  if (state.loading) return <Loading />;
  if (state.error) return <ErrorBox message={state.error} />;
  if (!state.items.length) return empty;
  return (
    <div>
      {state.items.map((item) => (item.type === "post"
        ? <PostCard key={`p${item.id}`} post={item} onChanged={changed} />
        : <WorkoutCard key={`w${item.id}`} workout={item} onChanged={changed} />))}
      {state.hasMore && <div className="actions right"><button className="btn" type="button" onClick={loadMore}>Показати ще</button></div>}
    </div>
  );
}
