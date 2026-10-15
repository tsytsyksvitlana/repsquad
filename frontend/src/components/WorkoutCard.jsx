import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useToast } from "../context/ToastContext.jsx";
import { fmtDay, num, plural, setsLabel, setsLine } from "../utils.js";
import { Avatar, VisibilityBadge } from "./common.jsx";

/** Like toggle for a workout (default) or any other item via `path` (e.g. a post). */
export function LikeButton({ workout, path }) {
  const toast = useToast();
  const [state, setState] = useState({ liked: workout.liked_by_me, likes: workout.likes });
  const toggle = async () => {
    try {
      const r = await api("POST", path || `/api/workouts/${workout.id}/like`, {});
      setState({ liked: r.liked, likes: r.likes });
    } catch (e) { toast(e.message, "err"); }
  };
  return (
    <button className={`btn small ${state.liked ? "on" : ""}`} type="button" aria-pressed={state.liked} onClick={toggle}>
      ♥ <span className="n">{state.likes}</span>
    </button>
  );
}

/** Owner actions: toggle visibility and delete. `onChanged` tells the parent to refresh. */
export function OwnerActions({ workout, onChanged, afterDelete }) {
  const toast = useToast();
  const isPublic = workout.visibility === "public";

  const toggleVisibility = async () => {
    try {
      await api("PATCH", `/api/workouts/${workout.id}`, { visibility: isPublic ? "private" : "public" });
      toast(isPublic ? "Тренування тепер приватне" : "Тренування тепер публічне");
      onChanged();
    } catch (e) { toast(e.message, "err"); }
  };
  const remove = async () => {
    if (!confirm("Видалити тренування без можливості відновлення?")) return;
    try {
      await api("DELETE", `/api/workouts/${workout.id}`);
      toast("Тренування видалено");
      (afterDelete || onChanged)();
    } catch (e) { toast(e.message, "err"); }
  };
  return (
    <>
      <button className="btn small" type="button" onClick={toggleVisibility}>{isPublic ? "Зробити приватним" : "Зробити публічним"}</button>
      <button className="btn small danger" type="button" onClick={remove}>Видалити</button>
    </>
  );
}

export const WorkoutStats = ({ workout }) => (
  <span className="stats grow">{setsLabel(workout.sets_count)}{workout.volume_kg ? ` · ${num(workout.volume_kg)} кг обʼєм` : ""}</span>
);

export function WorkoutCard({ workout: w, onChanged }) {
  const shown = w.exercises.slice(0, 4);
  const more = w.exercises.length - shown.length;
  return (
    <article className="card workout">
      <header>
        <Avatar username={w.author.username} name={w.author.display_name} src={w.author.avatar_url} />
        <div className="who">
          <Link to={`/u/${w.author.username}`}>{w.author.display_name}</Link><br />
          <span className="muted small">@{w.author.username} · {fmtDay(w.date)}</span>
        </div>
        <VisibilityBadge visibility={w.visibility} />
      </header>
      <h3><Link to={`/w/${w.id}`}>{w.title}</Link></h3>
      <div>
        {shown.map((e, i) => <div className="ex-line" key={i}><b>{e.name}</b><span>{setsLine(e)}</span></div>)}
        {more > 0 && <div className="muted small">…і ще {more} {plural(more, "вправа", "вправи", "вправ")}</div>}
      </div>
      <footer>
        <LikeButton workout={w} />
        <Link className="btn small" to={`/w/${w.id}`}>Коментарі · {w.comments_count}</Link>
        <WorkoutStats workout={w} />
        {w.is_mine && <OwnerActions workout={w} onChanged={onChanged} />}
      </footer>
    </article>
  );
}
