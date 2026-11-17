import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import Avatar from "./Avatar.jsx";
import { Logo } from "./ui.jsx";

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
          <Avatar user={me} size="sm" /><span>{me.username}</span>
        </Link>
        <button className="btn small ghost" type="button" onClick={logout}>Вийти</button>
      </div>
    </header>
  );
}
