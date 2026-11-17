import { Link } from "react-router-dom";
import Avatar from "./Avatar.jsx";
import { VisibilityBadge } from "./ui.jsx";

/** Card header shared by workouts and posts: avatar, author link, "@login · date" line and visibility badge. */
export default function AuthorHeader({ author, when, visibility }) {
  return (
    <header>
      <Avatar user={author} />
      <div className="who">
        <Link to={`/u/${author.username}`}>{author.display_name}</Link><br />
        <span className="muted small">@{author.username} · {when}</span>
      </div>
      <VisibilityBadge visibility={visibility} />
    </header>
  );
}
