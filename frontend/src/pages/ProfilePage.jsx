import { useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { useAsync, useTitle } from "../hooks.js";
import { Avatar, EmptyCard, ErrorBox, KIND_OPTIONS, Loading, Modal, Segmented } from "../components/common.jsx";
import Composer from "../components/Composer.jsx";
import ItemList from "../components/ItemList.jsx";
import { resizeImage } from "../utils.js";
import { FollowButton } from "./PeoplePage.jsx";

const LEVELS = ["", "початківець", "середній", "просунутий", "професіонал"];

/** Picture chooser: `value` is undefined (unchanged), null (remove) or a new JPEG data URL. */
function AvatarPicker({ profile, value, onChange }) {
  const toast = useToast();
  const input = useRef(null);
  const shown = value === undefined ? profile.avatar_url : value;
  const pick = async (e) => {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    try { onChange(await resizeImage(file)); }
    catch { toast("Не вдалося прочитати зображення", "err"); }
  };
  return (
    <div className="avatar-picker">
      <Avatar username={profile.username} name={profile.display_name} src={shown} size="lg" />
      <div>
        <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={pick} />
        <button className="btn small" type="button" onClick={() => input.current.click()}>{shown ? "Змінити фото" : "Додати фото"}</button>
        {shown && <button className="btn small ghost danger" type="button" onClick={() => onChange(null)}>Видалити фото</button>}
        <p className="muted small">JPEG, PNG або WebP. Фото обрізається до квадрата.</p>
      </div>
    </div>
  );
}

function EditProfileModal({ profile, onClose, onSaved }) {
  const toast = useToast();
  const { setMe } = useAuth();
  const [avatar, setAvatar] = useState(undefined);
  const save = async (f) => {
    const body = Object.fromEntries(["display_name", "sport", "level", "goals", "bio"].map((k) => [k, f.get(k)]));
    if (avatar) await api("PUT", "/api/me/avatar", { image: avatar });
    else if (avatar === null && profile.avatar_url) await api("DELETE", "/api/me/avatar");
    setMe(await api("PATCH", "/api/me", body)); // the reply also carries the updated avatar_url
    toast("Профіль оновлено");
    onSaved();
  };
  return (
    <Modal title="Редагувати профіль" onSubmit={save} onClose={onClose}>
      <AvatarPicker profile={profile} value={avatar} onChange={setAvatar} />
      <label>Ім'я<input name="display_name" required maxLength={40} defaultValue={profile.display_name} /></label>
      <div className="row2">
        <label>Вид спорту<input name="sport" maxLength={40} defaultValue={profile.sport} placeholder="Пауерліфтинг" /></label>
        <label>Рівень
          <select name="level" defaultValue={profile.level}>
            {LEVELS.map((l) => <option key={l} value={l}>{l || "Не вказано"}</option>)}
          </select>
        </label>
      </div>
      <label>Цілі<input name="goals" maxLength={200} defaultValue={profile.goals} /></label>
      <label>Про себе<textarea name="bio" maxLength={300} defaultValue={profile.bio} /></label>
    </Modal>
  );
}

export default function ProfilePage() {
  const { username } = useParams();
  const [version, setVersion] = useState(0);
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
          <Avatar username={p.username} name={p.display_name} src={p.avatar_url} size="lg" />
          <div className="info">
            <h1>{p.display_name}</h1>
            <div className="muted">@{p.username}</div>
            <div style={{ marginTop: ".5rem" }}>
              {p.sport && <span className="chip">{p.sport}</span>}
              {p.level && <span className="chip">{p.level}</span>}
            </div>
            {p.goals && <p><b>Цілі:</b> {p.goals}</p>}
            {p.bio && <p>{p.bio}</p>}
            <div className="counts">
              <div><b>{p.workouts}</b><span>{p.is_me ? "тренувань" : "публічних тренувань"}</span></div>
              <div><b>{p.posts}</b><span>{p.posts === 1 ? "допис" : "дописів"}</span></div>
              <div><b>{p.followers}</b><span>підписників</span></div>
              <div><b>{p.following}</b><span>підписок</span></div>
            </div>
            {p.is_me
              ? <button className="btn" type="button" onClick={() => setEditing(true)}>Редагувати профіль</button>
              : <FollowButton large username={p.username} following={p.followed_by_me} onChange={() => setVersion((v) => v + 1)} />}
          </div>
        </div>
      </div>
      {p.is_me && <Composer onPosted={() => setVersion((v) => v + 1)} />}
      <div className="page-head">
        <h2 style={{ margin: 0 }}>{p.is_me ? "Ваші публікації" : "Публікації"}</h2>
        <Segmented options={KIND_OPTIONS} value={kind} onChange={setKind} />
      </div>
      <ItemList
        resetKey={`${username}-${kind}-${p.posts}`}
        onItemsChanged={() => setVersion((v) => v + 1)}
        fetchPage={(offset) => api("GET", `/api/users/${encodeURIComponent(username)}/timeline?kind=${kind}&limit=10&offset=${offset}`)}
        empty={<EmptyCard title={p.is_me ? "У вас ще немає публікацій" : "Публічних публікацій поки немає"} text={p.is_me ? "Напишіть допис або запишіть тренування." : "Приватне не відображається."} />}
      />
      {editing && <EditProfileModal profile={p} onClose={() => setEditing(false)} onSaved={() => setVersion((v) => v + 1)} />}
    </>
  );
}
