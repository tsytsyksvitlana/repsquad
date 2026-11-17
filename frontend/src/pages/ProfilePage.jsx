import { useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";
import { KIND_OPTIONS, PAGE_SIZE } from "../config.js";
import { useAsync, useRefresh, useTitle } from "../hooks.js";
import Avatar from "../components/Avatar.jsx";
import Composer from "../components/Composer.jsx";
import EditProfileModal from "../components/EditProfileModal.jsx";
import FollowButton from "../components/FollowButton.jsx";
import ItemList from "../components/ItemList.jsx";
import { EmptyCard, ErrorBox, Loading, Segmented } from "../components/ui.jsx";

const Count = ({ value, label }) => <div><b>{value}</b><span>{label}</span></div>;

export default function ProfilePage() {
  const { username } = useParams();
  const [version, refresh] = useRefresh();
  const [editing, setEditing] = useState(false);
  const [kind, setKind] = useState("all");
  const { data: p, error, loading } = useAsync(() => api("GET", `/api/users/${encodeURIComponent(username)}`), [username, version]);
  useTitle(p ? `${p.display_name} — RepSquad` : "Профіль — RepSquad");

  if (loading && !p) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  return (
    <>
      <div className="card">
        <div className="profile-head">
          <Avatar user={p} size="lg" />
          <div className="info">
            <h1>{p.display_name}</h1>
            <div className="muted">@{p.username}</div>
            <div className="mt-xs">
              {p.sport && <span className="chip">{p.sport}</span>}
              {p.level && <span className="chip">{p.level}</span>}
            </div>
            {p.goals && <p><b>Цілі:</b> {p.goals}</p>}
            {p.bio && <p>{p.bio}</p>}
            <div className="counts">
              <Count value={p.workouts} label={p.is_me ? "тренувань" : "публічних тренувань"} />
              <Count value={p.posts} label={p.posts === 1 ? "допис" : "дописів"} />
              <Count value={p.followers} label="підписників" />
              <Count value={p.following} label="підписок" />
            </div>
            {p.is_me
              ? <button className="btn" type="button" onClick={() => setEditing(true)}>Редагувати профіль</button>
              : <FollowButton large username={p.username} following={p.followed_by_me} onChange={refresh} />}
          </div>
        </div>
      </div>
      {p.is_me && <Composer onPosted={refresh} />}
      <div className="page-head">
        <h2 className="flush">{p.is_me ? "Ваші публікації" : "Публікації"}</h2>
        <Segmented options={KIND_OPTIONS} value={kind} onChange={setKind} />
      </div>
      <ItemList
        resetKey={`${username}-${kind}-${p.posts}`}
        onItemsChanged={refresh}
        fetchPage={(offset) => api("GET", `/api/users/${encodeURIComponent(username)}/timeline?kind=${kind}&limit=${PAGE_SIZE}&offset=${offset}`)}
        empty={<EmptyCard title={p.is_me ? "У вас ще немає публікацій" : "Публічних публікацій поки немає"} text={p.is_me ? "Напишіть допис або запишіть тренування." : "Приватне не відображається."} />}
      />
      {editing && <EditProfileModal profile={p} onClose={() => setEditing(false)} onSaved={refresh} />}
    </>
  );
}
