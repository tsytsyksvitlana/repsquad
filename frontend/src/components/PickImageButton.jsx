import { useRef } from "react";
import { IMAGE } from "../config.js";
import { useToast } from "../context/ToastContext.jsx";

/**
 * Button that opens the file dialog, converts the chosen picture with `convert(file)`
 * (see utils/image.js) and passes the resulting data URL to `onPicked`.
 */
export default function PickImageButton({ convert, onPicked, children }) {
  const toast = useToast();
  const input = useRef(null);
  const pick = async (e) => {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file) return;
    try { onPicked(await convert(file)); }
    catch { toast("Не вдалося прочитати зображення", "err"); }
  };
  return (
    <>
      <input ref={input} type="file" accept={IMAGE.accept} hidden onChange={pick} />
      <button className="btn small" type="button" onClick={() => input.current.click()}>{children}</button>
    </>
  );
}
