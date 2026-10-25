import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { SEARCH_DEBOUNCE_MS } from "../config.js";
import { useToast } from "../context/ToastContext.jsx";
import { useTitle } from "../hooks.js";
import Avatar from "../components/Avatar.jsx";
import FollowButton from "../components/FollowButton.jsx";
import { workoutsLabel } from "../utils/format.js";

function UserRow({ user }) {
  const [following, setFollowing] = useState(user.followed_by_me);
  return (
    <div className="user-row">
      <Avatar user={user} />
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
    }, query ? SEARCH_DEBOUNCE_MS : 0);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [query, toast]);

  return (
    <>
      <div className="page-head"><h1>Люди</h1></div>
      <div className="card">
        <input type="search" placeholder="Пошук за логіном або ім'ям" aria-label="Пошук користувачів" autoFocus
          value={query} onChange={(e) => setQuery(e.target.value)} />
        <div className="mt-sm">
          {users === null ? null : users.length ? users.map((u) => <UserRow key={u.username} user={u} />) : <p className="muted">Нікого не знайдено</p>}
        </div>
      </div>
    </>
  );
}
