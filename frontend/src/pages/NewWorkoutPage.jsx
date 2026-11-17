import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useDraft } from "../context/DraftContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { useAsync, useTitle } from "../hooks.js";
import ExerciseBlock from "../components/ExerciseBlock.jsx";
import { ErrorBox, Loading } from "../components/ui.jsx";
import { num, setsLabel, todayISO } from "../utils/format.js";
import { countSets, initialForm, newExercise, toPayload, totalVolume } from "../workoutForm.js";

export default function NewWorkoutPage() {
  useTitle("Нове тренування — RepSquad");
  const navigate = useNavigate();
  const toast = useToast();
  const { peekDraft, clearDraft } = useDraft();
  const { data: names, error, loading } = useAsync(async () => (await api("GET", "/api/exercises")).items, []);

  // The form starts from the AI draft when there is one; the draft is dropped when leaving the page.
  const [initial] = useState(() => initialForm(peekDraft()));
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

  const totalSets = countSets(exercises);
  const volume = totalVolume(exercises);

  const replaceExercise = (next) => setExercises((list) => list.map((e) => (e.id === next.id ? next : e)));

  const submit = async (e) => {
    e.preventDefault();
    setFormError("");
    try {
      const r = await api("POST", "/api/workouts", toPayload({ title, date, visibility, notes, exercises }));
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
        <label className="mt-md">Нотатки
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
