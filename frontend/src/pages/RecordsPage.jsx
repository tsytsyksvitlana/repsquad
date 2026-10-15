import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAsync, useTitle } from "../hooks.js";
import { EmptyCard, ErrorBox, Loading, Segmented } from "../components/common.jsx";
import LineChart from "../components/LineChart.jsx";
import { num, workoutsLabel } from "../utils.js";

const WEIGHTED_METRICS = [["best_1rm", "Розрахунковий 1RM"], ["max_weight_kg", "Макс. вага"], ["volume_kg", "Обʼєм"]];
const BODYWEIGHT_METRICS = [["max_reps", "Макс. повторень"]];

function Progress({ record }) {
  const metrics = record.bodyweight ? BODYWEIGHT_METRICS : WEIGHTED_METRICS;
  const [choice, setChoice] = useState(null);
  const metric = metrics.some(([k]) => k === choice) ? choice : metrics[0][0];
  const { data, error, loading } = useAsync(() => api("GET", `/api/me/progress?exercise=${encodeURIComponent(record.exercise)}`), [record.exercise]);

  if (error) return <ErrorBox message={error} />;
  return (
    <div className="card">
      <div className="page-head" style={{ marginBottom: ".4rem" }}>
        <h2 style={{ margin: 0 }}>{record.exercise}</h2>
        <Segmented options={metrics} value={metric} onChange={setChoice} />
      </div>
      {loading || !data ? <Loading /> : <LineChart points={data.points} metric={metric} />}
      <p className="muted small">1RM — розрахунковий одноповторний максимум за формулою Епплі: вага × (1 + повторення / 30).</p>
    </div>
  );
}

export default function RecordsPage() {
  useTitle("Рекорди — RepSquad");
  const { data, error, loading } = useAsync(() => api("GET", "/api/me/records"), []);
  const [selected, setSelected] = useState(null);

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  const items = data.items;
  if (!items.length) {
    return (
      <>
        <div className="page-head"><h1>Рекорди та прогрес</h1></div>
        <EmptyCard title="Ще немає даних" text="Запишіть тренування — і тут зʼявляться ваші рекорди та графіки.">
          <Link className="btn primary" to="/new">+ Нове тренування</Link>
        </EmptyCard>
      </>
    );
  }
  // By default the most frequently trained exercise is selected.
  const current = items.find((r) => r.exercise === selected) || [...items].sort((a, b) => b.workouts - a.workouts)[0];
  return (
    <>
      <div className="page-head"><h1>Рекорди та прогрес</h1></div>
      <div className="rec-grid">
        {items.map((r) => (
          <button key={r.exercise} type="button" className={`rec ${r.exercise === current.exercise ? "on" : ""}`} onClick={() => setSelected(r.exercise)}>
            <div className="name">{r.exercise}</div>
            <div className="big">{r.bodyweight ? `${r.max_reps} повт.` : `${num(r.max_weight_kg)} кг`}</div>
            <div className="sub">
              {r.bodyweight ? "рекорд повторень" : `× ${r.max_weight_reps} · 1RM ≈ ${num(r.best_1rm)} кг`}<br />{workoutsLabel(r.workouts)}
            </div>
          </button>
        ))}
      </div>
      <Progress key={current.exercise} record={current} />
    </>
  );
}
