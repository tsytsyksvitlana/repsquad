/**
 * Round avatar for any user-shaped object { username, display_name, avatar_url }.
 * `src` overrides the picture (null shows the initial), e.g. while the user is choosing a new one.
 */
export default function Avatar({ user, src = user.avatar_url, size = "" }) {
  let hue = 0;
  for (const ch of user.username) hue = (hue * 31 + ch.charCodeAt(0)) % 360;
  return (
    <span className={`avatar ${size}`} style={{ background: `hsl(${hue} 55% 45%)` }} aria-hidden="true">
      {src ? <img src={src} alt="" loading="lazy" /> : (user.display_name || user.username).trim().charAt(0)}
    </span>
  );
}
