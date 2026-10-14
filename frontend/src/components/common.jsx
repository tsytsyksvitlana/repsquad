import { useEffect, useRef, useState } from "react";
import { readToken } from "../api.js";
import { useVideos } from "../context/VideosContext.jsx";

/** Round avatar: the user's picture when `src` is set, otherwise a coloured circle with the initial. */
export function Avatar({ username, name, src, size = "" }) {
  let hue = 0;
  for (const ch of username) hue = (hue * 31 + ch.charCodeAt(0)) % 360;
  return (
    <span className={`avatar ${size}`} style={{ background: `hsl(${hue} 55% 45%)` }} aria-hidden="true">
      {src ? <img src={src} alt="" loading="lazy" /> : (name || username).trim().charAt(0)}
    </span>
  );
}

/** An <img> for protected files: <img src> cannot send the Authorization header, so the file is fetched first. */
export function AuthImage({ src, alt = "" }) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    let cancelled = false;
    let objectUrl = null;
    fetch(src, { headers: { Authorization: `Bearer ${readToken()}` } })
      .then((r) => (r.ok ? r.blob() : Promise.reject(new Error("image"))))
      .then((blob) => { if (!cancelled) { objectUrl = URL.createObjectURL(blob); setUrl(objectUrl); } })
      .catch(() => { /* the placeholder stays */ });
    return () => { cancelled = true; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [src]);
  return url ? <img src={url} alt={alt} /> : <div className="post-image-placeholder" />;
}

/** "All / Workouts / Posts" switch used above lists. */
export const KIND_OPTIONS = [["all", "Усе"], ["workouts", "Тренування"], ["posts", "Дописи"]];

export function Logo({ size = 26 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true">
      <rect width="24" height="24" rx="6" fill="currentColor" />
      <path d="M5 12h14M7 8v8M17 8v8M4 10v4M20 10v4" stroke="#fff" strokeWidth="2" strokeLinecap="round" fill="none" />
    </svg>
  );
}

export function EmptyCard({ title, text, children }) {
  return (
    <div className="card empty">
      <b>{title}</b>{text}
      {children && <div className="actions" style={{ justifyContent: "center" }}>{children}</div>}
    </div>
  );
}

export const ErrorBox = ({ message }) => <EmptyCard title="Щось пішло не так" text={message} />;

export const Loading = () => <p className="muted">Завантаження…</p>;

/** Segmented control: options is [[value, label], ...]. */
export function Segmented({ options, value, onChange }) {
  return (
    <div className="seg">
      {options.map(([key, label]) => (
        <button key={key} type="button" className={key === value ? "on" : ""} onClick={() => onChange(key)}>{label}</button>
      ))}
    </div>
  );
}

export function VisibilityBadge({ visibility }) {
  return visibility === "public"
    ? <span className="badge public">Публічне</span>
    : <span className="badge private">Приватне</span>;
}

/** "How to do it" button for exercises that have a built-in video; toggles an embedded YouTube player. */
export function VideoSlot({ name }) {
  const { videoFor } = useVideos();
  const [open, setOpen] = useState(false);
  const video = videoFor(name);
  if (!video) return null;
  return (
    <div className="vid">
      <button className="btn small" type="button" onClick={() => setOpen((o) => !o)}>▶ Як виконувати</button>
      {open && (
        <>
        <div className="vid-frame">
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${encodeURIComponent(video.video_id)}`}
            title={`Відео: ${name}`}
            loading="lazy"
            referrerPolicy="strict-origin-when-cross-origin"
            allow="accelerometer; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
        {/* YouTube refuses to play embeds on some origins (e.g. an IP address such as 127.0.0.1) */}
        <a className="vid-link small muted" href={`https://www.youtube.com/watch?v=${encodeURIComponent(video.video_id)}`} target="_blank" rel="noreferrer">
          Не відтворюється? Дивитись на YouTube ↗
        </a>
        </>
      )}
    </div>
  );
}

/**
 * Modal dialog built on the native <dialog>. `onSubmit` receives FormData of the inner form;
 * a thrown Error is shown inside the dialog.
 */
export function Modal({ title, submitLabel = "Зберегти", onSubmit, onClose, children }) {
  const ref = useRef(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const dlg = ref.current;
    if (dlg && !dlg.open) dlg.showModal();
    return () => { if (dlg && dlg.open) dlg.close(); };
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await onSubmit(new FormData(e.target));
      onClose();
    } catch (ex) { setError(ex.message); }
  };

  return (
    <dialog ref={ref} onClose={onClose}>
      <form onSubmit={submit}>
        <h2>{title}</h2>
        <div>{children}</div>
        <p className="form-error" role="alert">{error}</p>
        <div className="actions right">
          <button className="btn ghost" type="button" onClick={onClose}>Скасувати</button>
          <button className="btn primary" type="submit">{submitLabel}</button>
        </div>
      </form>
    </dialog>
  );
}
