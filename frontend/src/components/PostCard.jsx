import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useToast } from "../context/ToastContext.jsx";
import { fmtDT } from "../utils.js";
import { Avatar, AuthImage, VisibilityBadge } from "./common.jsx";
import Comments from "./Comments.jsx";
import { LikeButton } from "./WorkoutCard.jsx";

/** A plain post: text and an optional picture. The author can switch visibility or delete it. */
export function PostCard({ post: p, onChanged }) {
  const toast = useToast();
  const isPublic = p.visibility === "public";
  const [comments, setComments] = useState({ open: false, loading: false, list: null, count: p.comments_count });

  // The comment list is loaded only when the section is opened.
  const toggleComments = async () => {
    if (comments.open) return setComments((c) => ({ ...c, open: false }));
    if (comments.list) return setComments((c) => ({ ...c, open: true }));
    setComments((c) => ({ ...c, loading: true }));
    try {
      const full = await api("GET", `/api/posts/${p.id}`);
      setComments({ open: true, loading: false, list: full.comments, count: full.comments.length });
    } catch (e) {
      toast(e.message, "err");
      setComments((c) => ({ ...c, loading: false }));
    }
  };

  const toggleVisibility = async () => {
    try {
      await api("PATCH", `/api/posts/${p.id}`, { visibility: isPublic ? "private" : "public" });
      toast(isPublic ? "Допис тепер приватний" : "Допис тепер публічний");
      onChanged();
    } catch (e) { toast(e.message, "err"); }
  };
  const remove = async () => {
    if (!confirm("Видалити допис без можливості відновлення?")) return;
    try {
      await api("DELETE", `/api/posts/${p.id}`);
      toast("Допис видалено");
      onChanged();
    } catch (e) { toast(e.message, "err"); }
  };

  return (
    <article className="card post">
      <header>
        <Avatar username={p.author.username} name={p.author.display_name} src={p.author.avatar_url} />
        <div className="who">
          <Link to={`/u/${p.author.username}`}>{p.author.display_name}</Link><br />
          <span className="muted small">@{p.author.username} · {fmtDT(p.created_at)}</span>
        </div>
        <VisibilityBadge visibility={p.visibility} />
      </header>
      {p.body && <p className="post-body">{p.body}</p>}
      {p.image_url && <div className="post-image"><AuthImage src={p.image_url} alt="Фото до допису" /></div>}
      <footer>
        <LikeButton workout={p} path={`/api/posts/${p.id}/like`} />
        <button className={`btn small ${comments.open ? "on" : ""}`} type="button" disabled={comments.loading} onClick={toggleComments}>
          Коментарі · {comments.count}
        </button>
        <span className="grow" />
        {p.is_mine && (
          <>
            <button className="btn small" type="button" onClick={toggleVisibility}>{isPublic ? "Зробити приватним" : "Зробити публічним"}</button>
            <button className="btn small danger" type="button" onClick={remove}>Видалити</button>
          </>
        )}
      </footer>
      {comments.open && (
        <Comments compact initial={comments.list} addPath={`/api/posts/${p.id}/comments`} deletePath={(cid) => `/api/post-comments/${cid}`}
          onCount={(n) => setComments((c) => ({ ...c, count: n, list: null }))} />
      )}
    </article>
  );
}
