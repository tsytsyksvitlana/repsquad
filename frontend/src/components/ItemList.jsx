import { useCallback, useEffect, useState } from "react";
import { useAction, useRefresh } from "../hooks.js";
import { ErrorBox, Loading } from "./ui.jsx";
import { PostCard } from "./PostCard.jsx";
import { WorkoutCard } from "./WorkoutCard.jsx";

/**
 * Paged list of workouts and posts. `fetchPage(offset)` must resolve to { items, has_more }.
 * The list restarts when `resetKey` changes or when a card reports a change (then `onItemsChanged` is called too).
 */
export default function ItemList({ fetchPage, empty, resetKey, onItemsChanged }) {
  const run = useAction();
  const [state, setState] = useState({ items: [], hasMore: false, loading: true, error: null });
  const [version, refresh] = useRefresh();

  useEffect(() => {
    let cancelled = false;
    setState({ items: [], hasMore: false, loading: true, error: null });
    fetchPage(0)
      .then((page) => { if (!cancelled) setState({ items: page.items, hasMore: page.has_more, loading: false, error: null }); })
      .catch((e) => { if (!cancelled) setState({ items: [], hasMore: false, loading: false, error: e.message }); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey, version]);

  const loadMore = useCallback(() => run(async () => {
    const page = await fetchPage(state.items.length);
    setState((s) => ({ ...s, items: [...s.items, ...page.items], hasMore: page.has_more }));
  }), [fetchPage, state.items.length, run]);

  const changed = () => { refresh(); if (onItemsChanged) onItemsChanged(); };

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
