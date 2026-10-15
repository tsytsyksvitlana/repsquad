import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useToast } from "../context/ToastContext.jsx";
import { useTitle } from "../hooks.js";
import { Avatar } from "../components/common.jsx";
import { workoutsLabel } from "../utils.js";

export function FollowButton({ username, following, onChange, large = false }) {
  const toast = useToast();
  const toggle = async () => {
    try {
      await api(following ? "DELETE" : "POST", `/api/users/${encodeURIComponent(username)}/follow`, following ? undefined : {});
      onChange(!following);
    } catch (e) { toast(e.message, "err"); }
  };
  return (
    <button className={`btn ${large ? "" : "small"} ${following ? "" : "primary"}`} type="button" onClick={toggle}>
      {following ? "Ви підписані" : "Підписатися"}
    </button>
  );
}

function UserRow({ user }) {
  const [following, setFollowing] = useState(user.followed_by_me);
  return (
    <div className="user-row">
      <Avatar username={user.username} name={user.display_name} src={user.avatar_url} />
      <div className="info">
        <Link to={`/u/${user.username}`}>{user.display_name}</Link> <span className="muted small">@{user.username}</span><br />
        <span className="muted small">{[user.sport, user.level].filter(Boolean).join(" · ") || "Без опису"} · {workoutsLabel(user.workouts)}</span>
      </div>
      {user.is_me ? <span className="badge private">Це ви</span> : <FollowButton username={user.username} following={following} onChange={setFollowing} />}
    </div>
  );
}

export default function PeoplePage() {
  useTitle("Люди — RepSquad");
  const toast = useToast();
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState(null);

  // Debounced search; stale responses are ignored.
  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      api("GET", `/api/users?q=${encodeURIComponent(query.trim())}`)
        .then((r) => { if (!cancelled) setUsers(r.items); })
        .catch((e) => toast(e.message, "err"));
    }, query ? 250 : 0);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [query, toast]);

  return (
    <>
      <div className="page-head"><h1>Люди</h1></div>
      <div className="card">
        <input type="search" placeholder="Пошук за логіном або ім'ям" aria-label="Пошук користувачів" autoFocus
          value={query} onChange={(e) => setQuery(e.target.value)} />
        <div style={{ marginTop: ".6rem" }}>
          {users === null ? null : users.length ? users.map((u) => <UserRow key={u.username} user={u} />) : <p className="muted">Нікого не знайдено</p>}
        </div>
      </div>
    </>
  );
}
