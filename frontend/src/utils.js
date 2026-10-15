// Formatting helpers shared by pages and components.

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

/** Center-crops an image file to a square and downsizes it; resolves to a JPEG data URL. */
export async function resizeImage(file, size = 256) {
  const bitmap = await createImageBitmap(file);
  const side = Math.min(bitmap.width, bitmap.height);
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  canvas.getContext("2d").drawImage(bitmap, (bitmap.width - side) / 2, (bitmap.height - side) / 2, side, side, 0, 0, size, size);
  bitmap.close();
  return canvas.toDataURL("image/jpeg", 0.85);
}

/** Downsizes an image file to fit into maxSide x maxSide, keeping its aspect ratio; resolves to a JPEG data URL. */
export async function fitImage(file, maxSide = 1080) {
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return canvas.toDataURL("image/jpeg", 0.85);
}

export const setsLabel = (n) => `${n} ${plural(n, "підхід", "підходи", "підходів")}`;
export const workoutsLabel = (n) => `${n} ${plural(n, "тренування", "тренування", "тренувань")}`;
