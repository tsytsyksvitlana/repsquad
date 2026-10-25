import { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { resizeImage } from "../utils/image.js";
import Avatar from "./Avatar.jsx";
import Modal from "./Modal.jsx";
import PickImageButton from "./PickImageButton.jsx";

const LEVELS = ["", "початківець", "середній", "просунутий", "професіонал"];
const PROFILE_FIELDS = ["display_name", "sport", "level", "goals", "bio"];

/** Picture chooser: `value` is undefined (unchanged), null (remove) or a new JPEG data URL. */
function AvatarPicker({ profile, value, onChange }) {
  const shown = value === undefined ? profile.avatar_url : value;
  return (
    <div className="avatar-picker">
      <Avatar user={profile} src={shown} size="lg" />
      <div>
        <PickImageButton convert={resizeImage} onPicked={onChange}>{shown ? "Змінити фото" : "Додати фото"}</PickImageButton>
        {shown && <button className="btn small ghost danger" type="button" onClick={() => onChange(null)}>Видалити фото</button>}
        <p className="muted small">JPEG, PNG або WebP. Фото обрізається до квадрата.</p>
      </div>
    </div>
  );
}

export default function EditProfileModal({ profile, onClose, onSaved }) {
  const toast = useToast();
  const { setMe } = useAuth();
  const [avatar, setAvatar] = useState(undefined);
  const save = async (f) => {
    const body = Object.fromEntries(PROFILE_FIELDS.map((k) => [k, f.get(k)]));
    if (avatar) await api("PUT", "/api/me/avatar", { image: avatar });
    else if (avatar === null && profile.avatar_url) await api("DELETE", "/api/me/avatar");
    setMe(await api("PATCH", "/api/me", body)); // the reply also carries the updated avatar_url
    toast("Профіль оновлено");
    onSaved();
  };
  return (
    <Modal title="Редагувати профіль" onSubmit={save} onClose={onClose}>
      <AvatarPicker profile={profile} value={avatar} onChange={setAvatar} />
      <label>Ім'я<input name="display_name" required maxLength={40} defaultValue={profile.display_name} /></label>
      <div className="row2">
        <label>Вид спорту<input name="sport" maxLength={40} defaultValue={profile.sport} placeholder="Пауерліфтинг" /></label>
        <label>Рівень
          <select name="level" defaultValue={profile.level}>
            {LEVELS.map((l) => <option key={l} value={l}>{l || "Не вказано"}</option>)}
          </select>
        </label>
      </div>
      <label>Цілі<input name="goals" maxLength={200} defaultValue={profile.goals} /></label>
      <label>Про себе<textarea name="bio" maxLength={300} defaultValue={profile.bio} /></label>
    </Modal>
  );
}
