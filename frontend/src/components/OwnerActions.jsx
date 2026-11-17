import { api } from "../api.js";
import { ITEM_KINDS } from "../config.js";
import { useAction } from "../hooks.js";

/**
 * Owner actions for a workout or a post: toggle visibility and delete.
 * `onChanged` tells the parent to refresh; `afterDelete` (optional) replaces it after a deletion.
 */
export default function OwnerActions({ kind, item, onChanged, afterDelete }) {
  const run = useAction();
  const text = ITEM_KINDS[kind];
  const isPublic = item.visibility === "public";

  const toggleVisibility = async () => {
    const done = await run(
      () => api("PATCH", `${text.path}/${item.id}`, { visibility: isPublic ? "private" : "public" }),
      isPublic ? text.madePrivate : text.madePublic,
    );
    if (done) onChanged();
  };
  const remove = async () => {
    if (!confirm(text.confirmDelete)) return;
    if (await run(() => api("DELETE", `${text.path}/${item.id}`), text.deleted)) (afterDelete || onChanged)();
  };

  return (
    <>
      <button className="btn small" type="button" onClick={toggleVisibility}>{isPublic ? "Зробити приватним" : "Зробити публічним"}</button>
      <button className="btn small danger" type="button" onClick={remove}>Видалити</button>
    </>
  );
}
