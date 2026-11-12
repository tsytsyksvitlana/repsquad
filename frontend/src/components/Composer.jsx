import { useState } from "react";
import { api } from "../api.js";
import { useToast } from "../context/ToastContext.jsx";
import { fitImage } from "../utils/image.js";
import PickImageButton from "./PickImageButton.jsx";
import { Segmented } from "./ui.jsx";

const VISIBILITY_OPTIONS = [["public", "Публічний"], ["private", "Приватний"]];

/** Form for writing a post (text and/or one picture). `onPosted` lets the parent refresh its list. */
export default function Composer({ onPosted }) {
  const toast = useToast();
  const [body, setBody] = useState("");
  const [visibility, setVisibility] = useState("public");
  const [image, setImage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api("POST", "/api/posts", { body, visibility, image });
      setBody(""); setImage(null);
      toast(visibility === "public" ? "Допис опубліковано" : "Допис збережено (приватний)");
      onPosted();
    } catch (ex) { setError(ex.message); }
    finally { setBusy(false); }
  };

  return (
    <form className="card composer" onSubmit={submit}>
      <textarea maxLength={1000} rows={3} placeholder="Чим хочете поділитися? Досягнення, думки, поради…" aria-label="Текст допису"
        value={body} onChange={(e) => setBody(e.target.value)} />
      {image && (
        <div className="composer-preview">
          <img src={image} alt="Попередній перегляд" />
          <button className="icon-btn" type="button" aria-label="Прибрати фото" title="Прибрати фото" onClick={() => setImage(null)}>×</button>
        </div>
      )}
      <div className="actions">
        <PickImageButton convert={fitImage} onPicked={setImage}>{image ? "Змінити фото" : "Додати фото"}</PickImageButton>
        <Segmented options={VISIBILITY_OPTIONS} value={visibility} onChange={setVisibility} />
        <span className="grow" />
        <button className="btn primary" type="submit" disabled={busy || (!body.trim() && !image)}>Опублікувати</button>
      </div>
      <p className="form-error" role="alert">{error}</p>
    </form>
  );
}
