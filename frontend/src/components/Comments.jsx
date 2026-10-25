import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAction } from "../hooks.js";
import { fmtDT } from "../utils/format.js";
import Avatar from "./Avatar.jsx";

/**
 * Comment list with a form, shared by workouts and posts.
 * `addPath` receives new comments (POST), `deletePath(id)` removes one (DELETE); both reply with { comments }.
 * `onCount` reports the new number of comments so a parent can keep its counter in sync.
 */
export default function Comments({ initial, addPath, deletePath, onCount, compact = false }) {
  const run = useAction();
  const [comments, setComments] = useState(initial);
  const [error, setError] = useState("");
  const [body, setBody] = useState("");

  const update = (list) => { setComments(list); if (onCount) onCount(list.length); };
  const add = async (e) => {
    e.preventDefault();
    setError("");
    try {
      update((await api("POST", addPath, { body })).comments);
      setBody("");
    } catch (ex) { setError(ex.message); }
  };
  const remove = (id) => run(async () => update((await api("DELETE", deletePath(id))).comments));

  return (
    <div className={compact ? "comments-inline" : "card"}>
      {!compact && <h2>Коментарі {comments.length > 0 && <span className="muted">({comments.length})</span>}</h2>}
      <div>
        {comments.length ? comments.map((c) => (
          <div className="comment" key={c.id}>
            <Avatar user={c.author} size="sm" />
            <div className="body">
              <div className="meta"><Link to={`/u/${c.author.username}`}><b>{c.author.display_name}</b></Link> · {fmtDT(c.created_at)}</div>
              {c.body}
            </div>
            {c.can_delete && <button className="icon-btn" type="button" aria-label="Видалити коментар" title="Видалити" onClick={() => remove(c.id)}>×</button>}
          </div>
        )) : <p className="muted">Поки немає коментарів. Будьте першим!</p>}
      </div>
      <form className="inline mt-sm" onSubmit={add}>
        <input required maxLength={500} placeholder="Напишіть коментар або пораду…" aria-label="Коментар" value={body} onChange={(e) => setBody(e.target.value)} />
        <button className="btn primary" type="submit">Надіслати</button>
      </form>
      <p className="form-error" role="alert">{error}</p>
    </div>
  );
}
