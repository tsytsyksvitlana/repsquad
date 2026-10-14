import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { Avatar, Logo } from "./common.jsx";

const NAV = [
  ["feed", "Стрічка"], ["discover", "Огляд"], ["search", "Люди"], ["new", "Нове тренування"],
  ["ai", "AI-тренер"], ["mine", "Мої тренування"], ["records", "Рекорди"],
];

export default function Topbar() {
  const { me, logout } = useAuth();
  return (
    <header className="topbar">
      <Link className="brand" to="/feed" aria-label="RepSquad — стрічка"><Logo /><span>RepSquad</span></Link>
      <nav className="nav" aria-label="Основна навігація">
        {NAV.map(([path, label]) => <NavLink key={path} to={`/${path}`} className={({ isActive }) => (isActive ? "active" : "")}>{label}</NavLink>)}
      </nav>
      <div className="me">
        <Link className="userlink" to={`/u/${me.username}`}>
          <Avatar username={me.username} name={me.display_name} src={me.avatar_url} size="sm" /><span>{me.username}</span>
        </Link>
        <button className="btn small ghost" type="button" onClick={logout}>Вийти</button>
      </div>
    </header>
  );
}
