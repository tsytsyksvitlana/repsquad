import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useToast } from "../context/ToastContext.jsx";
import { useAsync, useTitle } from "../hooks.js";
import { Avatar, ErrorBox, Loading, VideoSlot, VisibilityBadge } from "../components/common.jsx";
import Comments from "../components/Comments.jsx";
import { LikeButton, OwnerActions, WorkoutStats } from "../components/WorkoutCard.jsx";
import { fmtDay, fmtDT, num } from "../utils.js";

export default function WorkoutPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [version, setVersion] = useState(0);
  const { data: w, error, loading } = useAsync(() => api("GET", `/api/workouts/${id}`), [id, version]);
  useTitle(w ? `${w.title} — RepSquad` : "Тренування — RepSquad");

  // Scroll to top when opening another workout.
  useEffect(() => { window.scrollTo(0, 0); }, [id]);

  if (loading && !w) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  return (
    <>
      <article className="card workout">
        <header>
          <Avatar username={w.author.username} name={w.author.display_name} src={w.author.avatar_url} />
          <div className="who">
            <Link to={`/u/${w.author.username}`}>{w.author.display_name}</Link><br />
            <span className="muted small">@{w.author.username} · {fmtDay(w.date)}</span>
          </div>
          <VisibilityBadge visibility={w.visibility} />
        </header>
        <h1>{w.title}</h1>
        {w.exercises.map((e, i) => (
          <div key={i}>
            <h3>{e.name}</h3>
            <VideoSlot name={e.name} />
            <table className="sets-table">
              <thead><tr><th>Підхід</th><th>Повторень</th><th>Вага</th></tr></thead>
              <tbody>
                {e.sets.map((s, j) => (
                  <tr key={j}><td>{j + 1}</td><td>{s.reps}</td><td>{s.weight_kg > 0 ? `${num(s.weight_kg)} кг` : "власна вага"}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
        {w.notes && <p><b>Нотатки:</b> {w.notes}</p>}
        <footer>
          <LikeButton workout={w} />
          <WorkoutStats workout={w} />
          {w.is_mine && <OwnerActions workout={w} onChanged={() => setVersion((v) => v + 1)} afterDelete={() => navigate("/mine")} />}
        </footer>
      </article>
      <Comments key={w.id} initial={w.comments} addPath={`/api/workouts/${w.id}/comments`} deletePath={(cid) => `/api/comments/${cid}`} />
    </>
  );
}
