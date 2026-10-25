import { api } from "../api.js";
import { useAction } from "../hooks.js";

export default function FollowButton({ username, following, onChange, large = false }) {
  const run = useAction();
  const toggle = () => run(async () => {
    await api(following ? "DELETE" : "POST", `/api/users/${encodeURIComponent(username)}/follow`, following ? undefined : {});
    onChange(!following);
  });
  return (
    <button className={`btn ${large ? "" : "small"} ${following ? "" : "primary"}`} type="button" onClick={toggle}>
      {following ? "Ви підписані" : "Підписатися"}
    </button>
  );
}
