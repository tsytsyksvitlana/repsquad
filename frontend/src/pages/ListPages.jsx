import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { KIND_OPTIONS, PAGE_SIZE } from "../config.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useRefresh, useTitle } from "../hooks.js";
import { EmptyCard, Segmented } from "../components/ui.jsx";
import Composer from "../components/Composer.jsx";
import ItemList from "../components/ItemList.jsx";

const EMPTY_TEXT = {
  all: "Тут з'являться тренування й дописи.",
  workouts: "Тренувань поки немає.",
  posts: "Дописів поки немає.",
};

/**
 * Shared layout of the feed and discover pages: a title with the All/Workouts/Posts switch,
 * optional content above the intro line, and a paged list from `endpoint`.
 * `empty(kind)` renders the placeholder; `refreshKey` restarts the list from outside.
 */
function KindListPage({ title, intro, endpoint, empty, above = null, refreshKey = 0 }) {
  useTitle(`${title} — RepSquad`);
  const [kind, setKind] = useState("all");
  return (
    <>
      <div className="page-head">
        <h1>{title}</h1>
        <Segmented options={KIND_OPTIONS} value={kind} onChange={setKind} />
      </div>
      {above}
      <p className="muted small">{intro}</p>
      <ItemList
        resetKey={`${kind}-${refreshKey}`}
        fetchPage={(offset) => api("GET", `${endpoint}?kind=${kind}&limit=${PAGE_SIZE}&offset=${offset}`)}
        empty={empty(kind)}
      />
    </>
  );
}

export function FeedPage() {
  const [version, refresh] = useRefresh();
  return (
    <KindListPage
      title="Стрічка"
      intro="Публічні тренування й дописи тих, на кого ви підписані, та ваші власні дописи."
      endpoint="/api/feed"
      refreshKey={version}
      above={<Composer onPosted={refresh} />}
      empty={(kind) => (
        <EmptyCard title="Тут поки порожньо" text={`${EMPTY_TEXT[kind]} Підпишіться на спортсменів, щоб бачити їхні публікації.`}>
          <Link className="btn primary" to="/search">Знайти людей</Link>
          <Link className="btn" to="/discover">Переглянути огляд</Link>
        </EmptyCard>
      )}
    />
  );
}

export function DiscoverPage() {
  return (
    <KindListPage
      title="Огляд"
      intro="Усі публічні тренування й дописи"
      endpoint="/api/discover"
      empty={() => <EmptyCard title="Ще ніхто нічим не поділився" text="Зробіть тренування чи допис публічними — і вони зʼявляться тут." />}
    />
  );
}

const VISIBILITY_FILTER = [["", "Усі"], ["public", "Публічні"], ["private", "Приватні"]];

export function MinePage() {
  useTitle("Мої тренування — RepSquad");
  const { me } = useAuth();
  const [filter, setFilter] = useState("");
  const query = filter ? `&visibility=${filter}` : "";
  return (
    <>
      <div className="page-head">
        <h1>Мої тренування</h1>
        <Segmented options={VISIBILITY_FILTER} value={filter} onChange={setFilter} />
      </div>
      <p className="muted small">Приватні тренування бачите лише ви. Публічні — усі користувачі RepSquad.</p>
      <ItemList
        resetKey={filter}
        fetchPage={(offset) => api("GET", `/api/users/${encodeURIComponent(me.username)}/workouts?limit=${PAGE_SIZE}&offset=${offset}${query}`)}
        empty={(
          <EmptyCard title="Тренувань не знайдено" text="Запишіть перше тренування.">
            <Link className="btn primary" to="/new">+ Нове тренування</Link>
          </EmptyCard>
        )}
      />
    </>
  );
}
