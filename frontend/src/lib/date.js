// Dates in Asia/Seoul (SDD 6.0.2): "YYYY-MM-DD HH:mm", lists show the date only.
const parts = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Seoul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

function pick(iso) {
  const map = {};
  for (const { type, value } of parts.formatToParts(new Date(iso)))
    map[type] = value;
  return map;
}

export function formatDate(iso) {
  if (!iso) return "";
  const p = pick(iso);
  return `${p.year}-${p.month}-${p.day}`;
}

export function formatDateTime(iso) {
  if (!iso) return "";
  const p = pick(iso);
  return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}`;
}
