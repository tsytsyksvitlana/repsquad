import { useState } from "react";
import { useVideos } from "../context/VideosContext.jsx";

/** "How to do it" button for exercises that have a built-in video; toggles an embedded YouTube player. */
export default function VideoSlot({ name }) {
  const { videoFor } = useVideos();
  const [open, setOpen] = useState(false);
  const video = videoFor(name);
  if (!video) return null;
  const id = encodeURIComponent(video.video_id);
  return (
    <div className="vid">
      <button className="btn small" type="button" onClick={() => setOpen((o) => !o)}>▶ Як виконувати</button>
      {open && (
        <>
          <div className="vid-frame">
            <iframe
              src={`https://www.youtube-nocookie.com/embed/${id}`}
              title={`Відео: ${name}`}
              loading="lazy"
              referrerPolicy="strict-origin-when-cross-origin"
              allow="accelerometer; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            />
          </div>
          {/* YouTube refuses to play embeds on some origins (e.g. an IP address such as 127.0.0.1) */}
          <a className="vid-link small muted" href={`https://www.youtube.com/watch?v=${id}`} target="_blank" rel="noreferrer">
            Не відтворюється? Дивитись на YouTube ↗
          </a>
        </>
      )}
    </div>
  );
}
