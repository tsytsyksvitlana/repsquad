// Small presentational pieces used across pages.

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
      {children && <div className="actions center">{children}</div>}
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
