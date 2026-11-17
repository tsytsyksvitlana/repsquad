import { useState } from "react";
import { api } from "../api.js";
import { ITEM_KINDS } from "../config.js";
import { useAction } from "../hooks.js";

/** Like toggle for a workout or a post (`kind` is a key of ITEM_KINDS). */
export default function LikeButton({ kind, item }) {
  const run = useAction();
  const [state, setState] = useState({ liked: item.liked_by_me, likes: item.likes });
  const toggle = () => run(async () => {
    const r = await api("POST", `${ITEM_KINDS[kind].path}/${item.id}/like`, {});
    setState({ liked: r.liked, likes: r.likes });
  });
  return (
    <button className={`btn small ${state.liked ? "on" : ""}`} type="button" aria-pressed={state.liked} onClick={toggle}>
      ♥ <span className="n">{state.likes}</span>
    </button>
  );
}
