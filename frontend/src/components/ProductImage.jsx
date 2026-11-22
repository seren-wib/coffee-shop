import { useState } from "react";

const FALLBACK = "/default-bean.svg";

// image_url, or the default picture when it is missing or fails to load (SRS 7.1).
export default function ProductImage({
  src,
  alt,
  className = "",
  lazy = true,
}) {
  const [failed, setFailed] = useState(false);
  return (
    <img
      src={!src || failed ? FALLBACK : src}
      alt={alt}
      loading={lazy ? "lazy" : undefined}
      onError={() => setFailed(true)}
      className={`bg-cream-100 object-cover ${className}`}
    />
  );
}
