import { Link } from "react-router-dom";
import { fmtDay, num, plural, setsLabel, setsLine } from "../utils/format.js";
import AuthorHeader from "./AuthorHeader.jsx";
import LikeButton from "./LikeButton.jsx";
import OwnerActions from "./OwnerActions.jsx";

const PREVIEW_EXERCISES = 4;

export const WorkoutStats = ({ workout }) => (
  <span className="stats grow">{setsLabel(workout.sets_count)}{workout.volume_kg ? ` · ${num(workout.volume_kg)} кг обʼєм` : ""}</span>
);

export function WorkoutCard({ workout: w, onChanged }) {
  const shown = w.exercises.slice(0, PREVIEW_EXERCISES);
  const more = w.exercises.length - shown.length;
  return (
    <article className="card workout">
      <AuthorHeader author={w.author} when={fmtDay(w.date)} visibility={w.visibility} />
      <h3><Link to={`/w/${w.id}`}>{w.title}</Link></h3>
      <div>
        {shown.map((e, i) => <div className="ex-line" key={i}><b>{e.name}</b><span>{setsLine(e)}</span></div>)}
        {more > 0 && <div className="muted small">…і ще {more} {plural(more, "вправа", "вправи", "вправ")}</div>}
      </div>
      <footer>
        <LikeButton kind="workout" item={w} />
        <Link className="btn small" to={`/w/${w.id}`}>Коментарі · {w.comments_count}</Link>
        <WorkoutStats workout={w} />
        {w.is_mine && <OwnerActions kind="workout" item={w} onChanged={onChanged} />}
      </footer>
    </article>
  );
}
