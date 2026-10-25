import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAsync, useRefresh, useTitle } from "../hooks.js";
import { ErrorBox, Loading } from "../components/ui.jsx";
import AuthorHeader from "../components/AuthorHeader.jsx";
import Comments from "../components/Comments.jsx";
import LikeButton from "../components/LikeButton.jsx";
import OwnerActions from "../components/OwnerActions.jsx";
import VideoSlot from "../components/VideoSlot.jsx";
import { WorkoutStats } from "../components/WorkoutCard.jsx";
import { fmtDay, num } from "../utils/format.js";

export default function WorkoutPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [version, refresh] = useRefresh();
  const { data: w, error, loading } = useAsync(() => api("GET", `/api/workouts/${id}`), [id, version]);
  useTitle(w ? `${w.title} — RepSquad` : "Тренування — RepSquad");

  // Scroll to top when opening another workout.
  useEffect(() => { window.scrollTo(0, 0); }, [id]);

  if (loading && !w) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  return (
    <>
      <article className="card workout">
        <AuthorHeader author={w.author} when={fmtDay(w.date)} visibility={w.visibility} />
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
          <LikeButton kind="workout" item={w} />
          <WorkoutStats workout={w} />
          {w.is_mine && <OwnerActions kind="workout" item={w} onChanged={refresh} afterDelete={() => navigate("/mine")} />}
        </footer>
      </article>
      <Comments key={w.id} initial={w.comments} addPath={`/api/workouts/${w.id}/comments`} deletePath={(cid) => `/api/comments/${cid}`} />
    </>
  );
}
