import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { listProducts } from "../api/products";
import Button from "../components/Button";
import Notice from "../components/Notice";
import Pagination from "../components/Pagination";
import ProductImage from "../components/ProductImage";
import SelectField from "../components/SelectField";
import TextField from "../components/TextField";
import { errorMessage, isOffline } from "../lib/errors";
import { formatWon } from "../lib/format";
import { ROAST_LEVEL, label } from "../lib/labels";
import { ORIGINS } from "../lib/origins";

const FILTER_KEYS = [
  "search",
  "origin",
  "roast_level",
  "min_price",
  "max_price",
  "page",
];

// Price choices map to min_price/max_price on the base price (SDD 7.1, 4.3.4).
const PRICE_RANGES = [
  { value: "", label: "전체" },
  { value: "-9999", label: "1만 원 미만" },
  { value: "10000-19999", label: "1만 ~ 2만 원" },
  { value: "20000-29999", label: "2만 ~ 3만 원" },
  { value: "30000-", label: "3만 원 이상" },
];

const ORIGIN_OPTIONS = [
  { value: "", label: "전체" },
  ...ORIGINS.map((o) => ({ value: o, label: o })),
];

const ROAST_OPTIONS = [
  { value: "", label: "전체" },
  ...Object.entries(ROAST_LEVEL).map(([value, name]) => ({
    value,
    label: name,
  })),
];

function readFilters(params) {
  const min = params.get("min_price") ?? "";
  const max = params.get("max_price") ?? "";
  return {
    search: params.get("search") ?? "",
    origin: params.get("origin") ?? "",
    roast_level: params.get("roast_level") ?? "",
    price: min || max ? `${min}-${max}` : "",
  };
}

// SCR-01 (FR-1 ~ FR-5, UC-1). The URL query is the single source of the conditions.
export default function ProductListPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const query = params.toString();
  // The answer is kept with the query it belongs to, so a new query shows the placeholder.
  const [loaded, setLoaded] = useState({
    query: null,
    data: null,
    error: null,
  });

  useEffect(() => {
    let active = true;
    const current = new URLSearchParams(query);
    const apiParams = {};
    for (const key of FILTER_KEYS) {
      if (current.get(key)) apiParams[key] = current.get(key);
    }
    listProducts(apiParams)
      .then((data) => {
        if (active) setLoaded({ query, data, error: null });
      })
      .catch((err) => {
        if (!active) return;
        if (err.response?.status === 404 && apiParams.page) {
          // Out-of-range page: back to page 1 with the same conditions (SDD 8.4).
          current.delete("page");
          navigate(current.toString() ? `/?${current}` : "/", {
            replace: true,
          });
          return;
        }
        setLoaded({ query, data: null, error: err });
      });
    return () => {
      active = false;
    };
  }, [query, navigate]);

  const fresh = loaded.query === query;
  const result = fresh ? loaded.data : null;
  const error = fresh ? loaded.error : null;
  const page = Number(params.get("page")) || 1;
  const lastPage = result ? Math.max(1, Math.ceil(result.count / 20)) : 1;

  return (
    <div className="flex flex-col gap-7 px-12 pt-10 pb-14">
      <div className="flex flex-col gap-1.5">
        <h1 className="font-serif text-[32px] font-bold">원두 목록</h1>
        {result && (
          <p className="text-brown-600 text-sm">
            원두 {result.count}종 · {page} / {lastPage} 페이지
          </p>
        )}
      </div>

      <FilterForm key={query} initial={readFilters(params)} />

      {error && (
        <Notice kind={isOffline(error) ? "offline" : "error"}>
          {errorMessage(error)}
        </Notice>
      )}

      {!result && !error && <CardGridPlaceholder />}

      {result && result.results.length === 0 && (
        <p className="text-brown-600 py-16 text-center text-[15px]">
          조건에 맞는 원두가 없습니다
        </p>
      )}

      {result && result.results.length > 0 && (
        <>
          <ul className="grid grid-cols-[repeat(auto-fill,minmax(232px,1fr))] gap-6">
            {result.results.map((product) => (
              <li key={product.product_id}>
                <ProductCard product={product} />
              </li>
            ))}
          </ul>
          <Pagination count={result.count} page={page} />
        </>
      )}
    </div>
  );
}

// Remounted per query (key), so the inputs always start from the URL.
function FilterForm({ initial }) {
  const navigate = useNavigate();
  const [form, setForm] = useState(initial);
  const set = (key) => (event) =>
    setForm({ ...form, [key]: event.target.value });

  function handleSubmit(event) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (form.search.trim()) next.set("search", form.search.trim());
    if (form.origin) next.set("origin", form.origin);
    if (form.price) {
      const [min, max] = form.price.split("-");
      if (min) next.set("min_price", min);
      if (max) next.set("max_price", max);
    }
    if (form.roast_level) next.set("roast_level", form.roast_level);
    navigate(next.toString() ? `/?${next}` : "/");
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border-cream-300 flex flex-wrap items-end gap-3 rounded-lg border p-4"
    >
      <TextField
        label="원두 이름"
        type="search"
        placeholder="예: 예가체프"
        value={form.search}
        onChange={set("search")}
        className="flex-[1_1_320px]"
      />
      <SelectField
        label="원산지"
        options={ORIGIN_OPTIONS}
        value={form.origin}
        onChange={set("origin")}
        className="flex-[0_1_180px]"
      />
      <SelectField
        label="가격"
        options={PRICE_RANGES}
        value={form.price}
        onChange={set("price")}
        className="flex-[0_1_180px]"
      />
      <SelectField
        label="로스팅"
        options={ROAST_OPTIONS}
        value={form.roast_level}
        onChange={set("roast_level")}
        className="flex-[0_1_180px]"
      />
      <Button type="submit">검색</Button>
      <Button variant="ghost" onClick={() => navigate("/")}>
        초기화
      </Button>
    </form>
  );
}

function ProductCard({ product }) {
  const soldOut = product.sales_status === "SOLD_OUT";
  const ink = soldOut ? "text-brown-600" : "text-brown-900";
  return (
    <Link
      to={`/products/${product.product_id}`}
      className="border-cream-300 text-brown-900 hover:border-brown-600 hover:text-brown-900 flex h-full flex-col overflow-hidden rounded-xl border bg-white no-underline"
    >
      <div className="relative">
        <ProductImage
          src={product.image_url}
          alt=""
          className="aspect-[4/3] w-full"
        />
        {soldOut && (
          <span className="bg-espresso-950 text-latte-100 absolute top-2.5 left-2.5 inline-flex items-center gap-1.5 rounded-sm px-2.5 py-1 text-xs font-medium">
            <span
              aria-hidden="true"
              className="bg-dot-red size-1.5 rounded-[1px]"
            />
            품절
          </span>
        )}
      </div>
      <div className="flex flex-col gap-1 px-4 pt-3.5 pb-4">
        <span className="text-brown-600 text-xs">
          {product.origin} · {label(ROAST_LEVEL, product.roast_level)}
        </span>
        <span className={`font-serif text-[17px] font-bold ${ink}`}>
          {product.name}
        </span>
        <span className={`text-base font-bold ${ink}`}>
          {formatWon(product.lowest_price)}~
        </span>
      </div>
    </Link>
  );
}

function CardGridPlaceholder() {
  return (
    <ul
      aria-hidden="true"
      className="grid grid-cols-[repeat(auto-fill,minmax(232px,1fr))] gap-6"
    >
      {Array.from({ length: 10 }, (_, i) => (
        <li
          key={i}
          className="border-cream-300 overflow-hidden rounded-xl border"
        >
          <div className="bg-cream-100 aspect-[4/3]" />
          <div className="flex flex-col gap-2 px-4 pt-3.5 pb-4">
            <div className="bg-cream-100 h-3 w-24 rounded-sm" />
            <div className="bg-cream-100 h-4 w-36 rounded-sm" />
            <div className="bg-cream-100 h-4 w-20 rounded-sm" />
          </div>
        </li>
      ))}
    </ul>
  );
}
