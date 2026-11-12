// Formatting helpers shared by pages and components (image processing lives in image.js).

export const fmtDay = (d) => new Date(d + "T00:00").toLocaleDateString("uk-UA", { day: "numeric", month: "long", year: "numeric" });
export const fmtShortDay = (d) => new Date(d + "T00:00").toLocaleDateString("uk-UA", { day: "numeric", month: "short" });
export const fmtDT = (iso) => new Date(iso).toLocaleString("uk-UA", { dateStyle: "short", timeStyle: "short" });
export const num = (n) => (Number.isInteger(n) ? String(n) : String(+n.toFixed(2)));

export const todayISO = () => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
};

/** Ukrainian plural form: plural(n, one, few, many). */
export const plural = (n, one, few, many) => {
  const a = n % 10, b = n % 100;
  return a === 1 && b !== 11 ? one : a >= 2 && a <= 4 && (b < 10 || b >= 20) ? few : many;
};

/** Normalised exercise name used as a lookup key (matches the backend's casefolded name_key). */
export const exKey = (name) => name.replace(/\s+/g, " ").trim().toLowerCase();

export const setText = (s) => (s.weight_kg > 0 ? `${s.reps}×${num(s.weight_kg)} кг` : `${s.reps} повт.`);

/** All sets of an exercise on one line; for holds (plank) "reps" are seconds. */
export const setsLine = (e) => e.sets.map((s) => (/планк/i.test(e.name) ? `${s.reps} с` : setText(s))).join(" · ");

export const setsLabel = (n) => `${n} ${plural(n, "підхід", "підходи", "підходів")}`;
export const workoutsLabel = (n) => `${n} ${plural(n, "тренування", "тренування", "тренувань")}`;
