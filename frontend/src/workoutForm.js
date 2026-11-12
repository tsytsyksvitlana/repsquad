// State model of the "new workout" form, kept apart from the React components.

let uid = 0;
const nextId = () => ++uid;

export const newSet = (reps = "", weight = "") => ({ id: nextId(), reps, weight });
export const newExercise = (name = "", sets = [newSet()]) => ({ id: nextId(), name, sets });

/** Initial form values: from an AI trainer draft when there is one, otherwise empty. */
export function initialForm(draft) {
  if (!draft) return { title: "", notes: "", exercises: [newExercise()], fromDraft: false };
  return {
    title: draft.title,
    notes: draft.notes,
    exercises: draft.exercises.map((e) => newExercise(e.name, e.sets.map((s) => newSet(s.reps, s.weight_kg || "")))),
    fromDraft: true,
  };
}

export const countSets = (exercises) => exercises.reduce((a, e) => a + e.sets.length, 0);

export const totalVolume = (exercises) =>
  exercises.reduce((a, e) => a + e.sets.reduce((s, x) => s + (Number(x.reps) || 0) * (Number(x.weight) || 0), 0), 0);

/** Request body for POST /api/workouts. */
export const toPayload = ({ title, date, visibility, notes, exercises }) => ({
  title, date, visibility, notes,
  exercises: exercises.map((x) => ({
    name: x.name.trim(),
    sets: x.sets.map((s) => ({ reps: Number(s.reps), weight_kg: Number(s.weight || 0) })),
  })),
});
