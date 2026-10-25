import { useState } from "react";
import { api } from "../api.js";
import { useAction } from "../hooks.js";
import { fmtDT } from "../utils/format.js";
import AuthImage from "./AuthImage.jsx";
import AuthorHeader from "./AuthorHeader.jsx";
import Comments from "./Comments.jsx";
import LikeButton from "./LikeButton.jsx";
import OwnerActions from "./OwnerActions.jsx";

/** A plain post: text and an optional picture. The author can switch visibility or delete it. */
export function PostCard({ post: p, onChanged }) {
  const run = useAction();
  const [comments, setComments] = useState({ open: false, loading: false, list: null, count: p.comments_count });

  // The comment list is loaded only when the section is opened.
  const toggleComments = async () => {
    if (comments.open) return setComments((c) => ({ ...c, open: false }));
    if (comments.list) return setComments((c) => ({ ...c, open: true }));
    setComments((c) => ({ ...c, loading: true }));
    const loaded = await run(async () => {
      const full = await api("GET", `/api/posts/${p.id}`);
      setComments({ open: true, loading: false, list: full.comments, count: full.comments.length });
    });
    if (!loaded) setComments((c) => ({ ...c, loading: false }));
  };

  return (
    <article className="card post">
      <AuthorHeader author={p.author} when={fmtDT(p.created_at)} visibility={p.visibility} />
      {p.body && <p className="post-body">{p.body}</p>}
      {p.image_url && <div className="post-image"><AuthImage src={p.image_url} alt="Фото до допису" /></div>}
      <footer>
        <LikeButton kind="post" item={p} />
        <button className={`btn small ${comments.open ? "on" : ""}`} type="button" disabled={comments.loading} onClick={toggleComments}>
          Коментарі · {comments.count}
        </button>
        <span className="grow" />
        {p.is_mine && <OwnerActions kind="post" item={p} onChanged={onChanged} />}
      </footer>
      {comments.open && (
        <Comments compact initial={comments.list} addPath={`/api/posts/${p.id}/comments`} deletePath={(cid) => `/api/post-comments/${cid}`}
          onCount={(n) => setComments((c) => ({ ...c, count: n, list: null }))} />
      )}
    </article>
  );
}
