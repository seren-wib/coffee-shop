import { Link } from "react-router-dom";

// Tabs without boxes: the current tab is bold with a 2px espresso underline (layout rules board).
// items: [{key, to, label, current, count}]
export default function Tabs({ label, items }) {
  return (
    <nav
      aria-label={label}
      className="border-cream-300 flex flex-wrap gap-7 border-b text-sm"
    >
      {items.map((item) => (
        <Link
          key={item.key}
          to={item.to}
          aria-current={item.current ? "page" : undefined}
          className={`inline-flex items-center gap-1.5 py-2.5 no-underline ${
            item.current
              ? "border-espresso-950 text-brown-900 hover:text-brown-900 -mb-px border-b-2 font-bold"
              : "text-brown-600 hover:text-brown-900"
          }`}
        >
          {item.label}
          {item.count > 0 && (
            <span className="bg-espresso-950 text-latte-100 inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-sm px-[5px] text-[11px] font-bold">
              {item.count}
            </span>
          )}
        </Link>
      ))}
    </nav>
  );
}
