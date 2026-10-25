import { useEffect, useRef, useState } from "react";

/**
 * Modal dialog built on the native <dialog>. `onSubmit` receives FormData of the inner form;
 * a thrown Error is shown inside the dialog.
 */
export default function Modal({ title, submitLabel = "Зберегти", onSubmit, onClose, children }) {
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
