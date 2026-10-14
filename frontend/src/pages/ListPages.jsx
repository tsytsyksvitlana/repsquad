import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useTitle } from "../hooks.js";
import { EmptyCard, KIND_OPTIONS, Segmented } from "../components/common.jsx";
import Composer from "../components/Composer.jsx";
import ItemList from "../components/ItemList.jsx";

const PAGE = 10;

const EMPTY_TEXT = {
  all: "Тут з'являться тренування й дописи.",
  workouts: "Тренувань поки немає.",
  posts: "Дописів поки немає.",
};

export function FeedPage() {
  useTitle("Стрічка — RepSquad");
  const [kind, setKind] = useState("all");
  const [version, setVersion] = useState(0);
  return (
    <>
      <div className="page-head">
        <h1>Стрічка</h1>
        <Segmented options={KIND_OPTIONS} value={kind} onChange={setKind} />
      </div>
      <Composer onPosted={() => setVersion((v) => v + 1)} />
      <p className="muted small">Публічні тренування й дописи тих, на кого ви підписані, та ваші власні дописи.</p>
      <ItemList
        resetKey={`${kind}-${version}`}
        fetchPage={(offset) => api("GET", `/api/feed?kind=${kind}&limit=${PAGE}&offset=${offset}`)}
        empty={(
          <EmptyCard title="Тут поки порожньо" text={`${EMPTY_TEXT[kind]} Підпишіться на спортсменів, щоб бачити їхні публікації.`}>
            <Link className="btn primary" to="/search">Знайти людей</Link>
            <Link className="btn" to="/discover">Переглянути огляд</Link>
          </EmptyCard>
        )}
      />
    </>
  );
}

export function DiscoverPage() {
  useTitle("Огляд — RepSquad");
  const [kind, setKind] = useState("all");
  return (
    <>
      <div className="page-head">
        <h1>Огляд</h1>
        <Segmented options={KIND_OPTIONS} value={kind} onChange={setKind} />
      </div>
      <p className="muted small">Усі публічні тренування й дописи</p>
      <ItemList
        resetKey={kind}
        fetchPage={(offset) => api("GET", `/api/discover?kind=${kind}&limit=${PAGE}&offset=${offset}`)}
        empty={<EmptyCard title="Ще ніхто нічим не поділився" text="Зробіть тренування чи допис публічними — і вони зʼявляться тут." />}
      />
    </>
  );
}

export function MinePage() {
  useTitle("Мої тренування — RepSquad");
  const { me } = useAuth();
  const [filter, setFilter] = useState("");
  const query = filter ? `&visibility=${filter}` : "";
  return (
    <>
      <div className="page-head">
        <h1>Мої тренування</h1>
        <Segmented options={[["", "Усі"], ["public", "Публічні"], ["private", "Приватні"]]} value={filter} onChange={setFilter} />
      </div>
      <p className="muted small">Приватні тренування бачите лише ви. Публічні — усі користувачі RepSquad.</p>
      <ItemList
        resetKey={filter}
        fetchPage={(offset) => api("GET", `/api/users/${encodeURIComponent(me.username)}/workouts?limit=${PAGE}&offset=${offset}${query}`)}
        empty={(
          <EmptyCard title="Тренувань не знайдено" text="Запишіть перше тренування.">
            <Link className="btn primary" to="/new">+ Нове тренування</Link>
          </EmptyCard>
        )}
      />
    </>
  );
}
