import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useDraft } from "../context/DraftContext.jsx";
import { useTitle } from "../hooks.js";
import VideoSlot from "../components/VideoSlot.jsx";
import { setsLine } from "../utils/format.js";

const IDEAS = [
  "Тренування на все тіло для початківця, 45 хвилин",
  "Груди й трицепс із гантелями вдома",
  "День ніг для спортсмена, 60 хвилин",
  "Коротке кардіо та прес без обладнання",
];

const WEIGHT_NOTES = {
  history: "Вага розрахована з ваших рекордів (із запасом у 2 повтори)",
  needs: "⚖ Вагу підберіть самі: почніть із легкої та додавайте поступово",
};

function DraftPreview({ draft, onRetry, onEdit }) {
  return (
    <div className="card">
      <h2>{draft.title}</h2>
      {draft.notes && <p className="muted">{draft.notes}</p>}
      {draft.exercises.map((x, i) => (
        <div className="ai-ex" key={i}>
          <div className="ex-line"><b>{x.name}</b><span>{setsLine(x)}</span></div>
          {WEIGHT_NOTES[x.weight_source] && <div className="muted small">{WEIGHT_NOTES[x.weight_source]}</div>}
          <VideoSlot name={x.name} />
        </div>
      ))}
      <div className="actions right">
        <button className="btn" type="button" onClick={onRetry}>Інший варіант</button>
        <button className="btn primary" type="button" onClick={onEdit}>Редагувати й зберегти</button>
      </div>
    </div>
  );
}

export default function AiPage() {
  useTitle("AI-тренер — RepSquad");
  const navigate = useNavigate();
  const { setDraft } = useDraft();
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [draft, setLocalDraft] = useState(null);

  const generate = async () => {
    setError("");
    setLocalDraft(null);
    setBusy(true);
    try {
      setLocalDraft((await api("POST", "/api/ai/workout", { prompt })).draft);
    } catch (ex) { setError(ex.message); }
    finally { setBusy(false); }
  };

  const edit = () => {
    setDraft(draft);
    navigate("/new");
  };

  return (
    <>
      <div className="page-head"><h1>AI-тренер</h1><span className="muted small">Опишіть, що потрібно, — і ми складемо тренування</span></div>
      <form className="card" onSubmit={(e) => { e.preventDefault(); generate(); }}>
        <label>Яке тренування вам потрібно?
          <textarea required maxLength={500} rows={3} placeholder="Наприклад: тренування на спину й біцепс, 5 вправ, у залі"
            value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        </label>
        <div className="ideas">
          {IDEAS.map((t) => <button key={t} type="button" className="chip" onClick={() => setPrompt(t)}>{t}</button>)}
        </div>
        <p className="muted small">
          Враховуємо ваш вид спорту, рівень і цілі з профілю. Це чернетка: перед збереженням її можна відредагувати.
          Ваги розраховуються з ваших рекордів; для вправ без історії їх треба підібрати самостійно.
        </p>
        <p className="form-error" role="alert">{error}</p>
        <div className="actions right">
          <button className="btn primary" type="submit" disabled={busy}>{busy ? "Складаємо тренування…" : "Скласти тренування"}</button>
        </div>
      </form>
      {draft && <DraftPreview draft={draft} onRetry={generate} onEdit={edit} />}
    </>
  );
}
