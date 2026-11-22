// Only same-site paths are accepted for ?next= to avoid an open redirect (SDD 4.1.4).
export function safeNext(next) {
  if (typeof next !== "string" || !next.startsWith("/")) return "/";
  if (next.startsWith("//") || next.startsWith("/\\")) return "/";
  return next;
}

export function loginPath(currentPath) {
  return `/login?next=${encodeURIComponent(currentPath)}`;
}
