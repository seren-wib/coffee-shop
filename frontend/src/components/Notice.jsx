// Notice strip: espresso, 4px corners, the kind is told by the dot color (components sheet).
const DOTS = {
  error: "bg-dot-red",
  success: "bg-dot-green",
  offline: "bg-brown-400",
};

export default function Notice({ kind = "error", children, className = "" }) {
  return (
    <div
      role={kind === "success" ? "status" : "alert"}
      className={`bg-espresso-950 text-latte-100 [&_a]:text-latte-100 flex items-center gap-2.5 rounded-sm px-3.5 py-2.5 text-sm ${className}`}
    >
      <span
        aria-hidden="true"
        className={`size-2 shrink-0 rounded-[1px] ${DOTS[kind]}`}
      />
      <span>{children}</span>
    </div>
  );
}
