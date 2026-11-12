import { useEffect, useState } from "react";
import { readToken } from "../api.js";

/** An <img> for protected files: <img src> cannot send the Authorization header, so the file is fetched first. */
export default function AuthImage({ src, alt = "" }) {
  const [url, setUrl] = useState(null);
  useEffect(() => {
    let cancelled = false;
    let objectUrl = null;
    fetch(src, { headers: { Authorization: `Bearer ${readToken()}` } })
      .then((r) => (r.ok ? r.blob() : Promise.reject(new Error("image"))))
      .then((blob) => { if (!cancelled) { objectUrl = URL.createObjectURL(blob); setUrl(objectUrl); } })
      .catch(() => { /* the placeholder stays */ });
    return () => { cancelled = true; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [src]);
  return url ? <img src={url} alt={alt} /> : <div className="post-image-placeholder" />;
}
