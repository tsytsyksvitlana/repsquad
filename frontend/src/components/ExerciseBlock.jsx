import { newSet } from "../workoutForm.js";
import VideoSlot from "./VideoSlot.jsx";

/** One exercise of the workout form: its name, video hint and the list of sets. Controlled by the parent. */
export default function ExerciseBlock({ exercise, canRemove, onChange, onRemove }) {
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
