import { Link, useLocation } from "react-router-dom";

const PAGE_SIZE = 20; // SDD 7.4, fixed on the server
const WINDOW = 10;

// No boxes: the current page is bold with a 2px underline (layout rules board).
export default function Pagination({ count, page }) {
  const { pathname, search } = useLocation();
  const last = Math.max(1, Math.ceil(count / PAGE_SIZE));
  if (last <= 1) return null;

  const hrefFor = (n) => {
    const params = new URLSearchParams(search);
    params.delete("page");
    if (n > 1) params.set("page", String(n));
    const query = params.toString();
    return query ? `${pathname}?${query}` : pathname;
  };

  const start = Math.max(
    1,
    Math.min(page - Math.floor(WINDOW / 2), last - WINDOW + 1),
  );
  const pages = [];
  for (let n = start; n <= Math.min(last, start + WINDOW - 1); n += 1)
    pages.push(n);

  const plain = "px-0.5 py-1 no-underline";
  return (
    <nav
      aria-label="페이지"
      className="flex items-center justify-center gap-5 text-sm"
    >
      {page > 1 ? (
        <Link
          to={hrefFor(page - 1)}
          className={`${plain} text-brown-900 hover:text-brown-900`}
        >
          이전
        </Link>
      ) : (
        <span className={`${plain} text-brown-600`}>이전</span>
      )}
      {pages.map((n) =>
        n === page ? (
          <Link
            key={n}
            to={hrefFor(n)}
            aria-current="page"
            className="text-brown-900 hover:text-brown-900 px-0.5 py-1 font-bold underline decoration-2 underline-offset-[6px]"
          >
            {n}
          </Link>
        ) : (
          <Link
            key={n}
            to={hrefFor(n)}
            className={`${plain} text-brown-600 hover:text-brown-900`}
          >
            {n}
          </Link>
        ),
      )}
      {page < last ? (
        <Link
          to={hrefFor(page + 1)}
          className={`${plain} text-brown-900 hover:text-brown-900`}
        >
          다음
        </Link>
      ) : (
        <span className={`${plain} text-brown-600`}>다음</span>
      )}
    </nav>
  );
}
