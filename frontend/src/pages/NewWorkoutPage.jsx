import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useDraft } from "../context/DraftContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { useAsync, useTitle } from "../hooks.js";
import { ErrorBox, Loading, VideoSlot } from "../components/common.jsx";
import { num, setsLabel, todayISO } from "../utils.js";

let uid = 0;
const nextId = () => ++uid;
const newSet = (reps = "", weight = "") => ({ id: nextId(), reps, weight });
const newExercise = (name = "", sets = [newSet()]) => ({ id: nextId(), name, sets });

/** Converts a draft from the AI trainer into form state. */
function fromDraft(draft) {
  return draft.exercises.map((e) => newExercise(e.name, e.sets.map((s) => newSet(s.reps, s.weight_kg || ""))));
}

function ExerciseBlock({ exercise, canRemove, onChange, onRemove }) {
  const setName = (name) => onChange({ ...exercise, name });
  const updateSet = (id, patch) => onChange({ ...exercise, sets: exercise.sets.map((s) => (s.id === id ? { ...s, ...patch } : s)) });
  const addSet = () => {
    const last = exercise.sets[exercise.sets.length - 1];
    onChange({ ...exercise, sets: [...exercise.sets, newSet(last.reps, last.weight)] });
  };
  const removeSet = (id) => onChange({ ...exercise, sets: exercise.sets.filter((s) => s.id !== id) });

  return (
    <div className="ex-block">
      <div className="ex-head">
        <input className="ex-name" list="ex-names" required maxLength={50} placeholder="Назва вправи" aria-label="Назва вправи"
          value={exercise.name} onChange={(e) => setName(e.target.value)} />
        <button className="icon-btn" type="button" aria-label="Видалити вправу" title="Видалити вправу" disabled={!canRemove} onClick={onRemove}>×</button>
      </div>
      {exercise.name && <VideoSlot name={exercise.name} />}
      <div className="set-head"><span></span><span>Повторень</span><span>Вага, кг</span><span></span></div>
      <div>
        {exercise.sets.map((s, i) => (
          <div className="set-row" key={s.id}>
            <span className="n">{i + 1}</span>
            <input type="number" min="1" max="100" step="1" required inputMode="numeric" aria-label="Повторень"
              value={s.reps} onChange={(e) => updateSet(s.id, { reps: e.target.value })} />
            <input type="number" min="0" max="1000" step="0.25" inputMode="decimal" aria-label="Вага, кг" placeholder="0"
              value={s.weight} onChange={(e) => updateSet(s.id, { weight: e.target.value })} />
            <button className="icon-btn" type="button" aria-label="Видалити підхід" title="Видалити підхід"
              disabled={exercise.sets.length === 1} onClick={() => removeSet(s.id)}>×</button>
          </div>
        ))}
      </div>
      <button className="btn small" type="button" onClick={addSet}>+ Підхід</button>
    </div>
  );
}

export default function NewWorkoutPage() {
  useTitle("Нове тренування — RepSquad");
  const navigate = useNavigate();
  const toast = useToast();
  const { peekDraft, clearDraft } = useDraft();
  const { data: names, error, loading } = useAsync(async () => (await api("GET", "/api/exercises")).items, []);

  // The form starts from the AI draft when there is one; the draft is dropped when leaving the page.
  const [initial] = useState(() => {
    const draft = peekDraft();
    return draft
      ? { title: draft.title, notes: draft.notes, exercises: fromDraft(draft), fromDraft: true }
      : { title: "", notes: "", exercises: [newExercise()], fromDraft: false };
  });
  useEffect(() => {
    if (initial.fromDraft) toast("Чернетку завантажено — перевірте й збережіть");
    return clearDraft;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [title, setTitle] = useState(initial.title);
  const [date, setDate] = useState(todayISO());
  const [visibility, setVisibility] = useState("private");
  const [notes, setNotes] = useState(initial.notes);
  const [exercises, setExercises] = useState(initial.exercises);
  const [formError, setFormError] = useState("");

  const totalSets = exercises.reduce((a, e) => a + e.sets.length, 0);
  const volume = exercises.reduce((a, e) => a + e.sets.reduce((s, x) => s + (Number(x.reps) || 0) * (Number(x.weight) || 0), 0), 0);

  const replaceExercise = (next) => setExercises((list) => list.map((e) => (e.id === next.id ? next : e)));

  const submit = async (e) => {
    e.preventDefault();
    setFormError("");
    try {
      const r = await api("POST", "/api/workouts", {
        title, date, visibility, notes,
        exercises: exercises.map((x) => ({
          name: x.name.trim(),
          sets: x.sets.map((s) => ({ reps: Number(s.reps), weight_kg: Number(s.weight || 0) })),
        })),
      });
      toast(r.workout.visibility === "public" ? "Тренування збережено та опубліковано" : "Тренування збережено (приватне)");
      r.new_records.forEach((rec) => toast(`Новий рекорд! ${rec.exercise}: ${num(rec.weight_kg)} кг (було ${num(rec.previous_kg)} кг)`, "pr"));
      navigate(`/w/${r.workout.id}`);
    } catch (ex) { setFormError(ex.message); }
  };

  if (loading) return <Loading />;
  if (error) return <ErrorBox message={error} />;
  return (
    <>
      <div className="page-head"><h1>Нове тренування</h1></div>
      <datalist id="ex-names">{names.map((n) => <option key={n} value={n} />)}</datalist>
      <form className="card" autoComplete="off" onSubmit={submit}>
        <div className="row2">
          <label>Назва<input required maxLength={60} placeholder="Наприклад, Груди й трицепс" value={title} onChange={(e) => setTitle(e.target.value)} /></label>
          <label>Дата<input type="date" required max={todayISO()} value={date} onChange={(e) => setDate(e.target.value)} /></label>
        </div>
        <div className="vis-choice" role="radiogroup" aria-label="Видимість тренування">
          <label>
            <input type="radio" name="visibility" value="private" checked={visibility === "private"} onChange={() => setVisibility("private")} />
            <span className="opt"><b>Приватне</b><small>Бачите лише ви</small></span>
          </label>
          <label>
            <input type="radio" name="visibility" value="public" checked={visibility === "public"} onChange={() => setVisibility("public")} />
            <span className="opt"><b>Публічне</b><small>Бачать усі користувачі</small></span>
          </label>
        </div>
        <div>
          {exercises.map((x) => (
            <ExerciseBlock key={x.id} exercise={x} canRemove={exercises.length > 1} onChange={replaceExercise}
              onRemove={() => setExercises((list) => list.filter((e) => e.id !== x.id))} />
          ))}
        </div>
        <div className="actions">
          <button className="btn" type="button" onClick={() => setExercises((list) => [...list, newExercise()])}>+ Додати вправу</button>
          <span className="total">{setsLabel(totalSets)}{volume ? ` · обʼєм ${num(volume)} кг` : ""}</span>
        </div>
        <label style={{ marginTop: "1rem" }}>Нотатки
          <textarea maxLength={500} placeholder="Самопочуття, техніка, що покращити…" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </label>
        <p className="form-error" role="alert">{formError}</p>
        <div className="actions right">
          <Link className="btn ghost" to="/mine">Скасувати</Link>
          <button className="btn primary" type="submit">Зберегти тренування</button>
        </div>
      </form>
    </>
  );
}
