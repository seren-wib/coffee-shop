import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { listAdminProducts, resumeSales, stopSales } from "../../api/admin";
import AdminTabs from "../../components/AdminTabs";
import Button from "../../components/Button";
import Notice from "../../components/Notice";
import Pagination from "../../components/Pagination";
import SelectField from "../../components/SelectField";
import StatusBadge from "../../components/StatusBadge";
import TextField from "../../components/TextField";
import { errorMessage, isOffline } from "../../lib/errors";
import { formatWon } from "../../lib/format";
import { ROAST_LEVEL, SALES_STATUS, label } from "../../lib/labels";

const STATUS_OPTIONS = [
  { value: "", label: "전체" },
  ...Object.entries(SALES_STATUS).map(([value, name]) => ({
    value,
    label: name,
  })),
];

const linkButton =
  "inline-flex h-7 items-center rounded-md border border-cream-300 bg-white px-2.5 text-[13px] text-brown-900 no-underline hover:bg-cream-100 hover:text-brown-900";

// SCR-11 (FR-36, FR-42, FR-43, FR-56). Stopped beans are listed too.
export default function AdminProductListPage() {
  const [params] = useSearchParams();
  const query = params.toString();
  const page = Number(params.get("page")) || 1;
  const [loaded, setLoaded] = useState({
    query: null,
    data: null,
    error: null,
  });
  const [actionError, setActionError] = useState(null);
  const [busy, setBusy] = useState(false);

  const fetchPage = useCallback(() => {
    const current = new URLSearchParams(query);
    const apiParams = {};
    for (const key of ["search", "sales_status", "page"]) {
      if (current.get(key)) apiParams[key] = current.get(key);
    }
    return listAdminProducts(apiParams);
  }, [query]);

  useEffect(() => {
    let active = true;
    fetchPage().then(
      (data) => active && setLoaded({ query, data, error: null }),
      (error) => active && setLoaded({ query, data: null, error }),
    );
    return () => {
      active = false;
    };
  }, [fetchPage, query]);

  async function toggle(product) {
    setBusy(true);
    setActionError(null);
    try {
      await (product.sales_status === "STOPPED" ? resumeSales : stopSales)(
        product.product_id,
      );
      const data = await fetchPage();
      setLoaded({ query, data, error: null });
    } catch (err) {
      setActionError(err);
    }
    setBusy(false);
  }

  const fresh = loaded.query === query;
  const result = fresh ? loaded.data : null;
  const error = fresh ? loaded.error : null;
  const shown = error ?? actionError;

  return (
    <div className="flex flex-col gap-6 px-12 pt-8 pb-14">
      <h1 className="sr-only">원두 관리</h1>
      <AdminTabs />
      <div className="flex flex-wrap items-end justify-between gap-4">
        <FilterForm key={query} />
        <Link
          to="/admin/products/new"
          className="bg-caramel-700 hover:bg-caramel-800 inline-flex h-8 items-center rounded-md px-3 text-sm font-medium text-white no-underline hover:text-white"
        >
          원두 등록
        </Link>
      </div>

      {shown && (
        <Notice kind={isOffline(shown) ? "offline" : "error"}>
          {errorMessage(shown)}
        </Notice>
      )}
      {!result && !error && (
        <div aria-hidden="true" className="bg-cream-100 h-60 rounded-xl" />
      )}
      {result?.results.length === 0 && (
        <p className="text-brown-600 py-16 text-center text-[15px]">
          조건에 맞는 원두가 없습니다
        </p>
      )}
      {result?.results.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[880px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-brown-900 text-brown-600 border-b text-[13px]">
                  <th scope="col" className="py-2.5 pr-4 font-medium">
                    ID
                  </th>
                  <th scope="col" className="py-2.5 pr-4 font-medium">
                    원두명
                  </th>
                  <th scope="col" className="py-2.5 pr-4 font-medium">
                    원산지
                  </th>
                  <th scope="col" className="py-2.5 pr-4 font-medium">
                    로스팅
                  </th>
                  <th
                    scope="col"
                    className="py-2.5 pr-4 text-right font-medium"
                  >
                    기본가격
                  </th>
                  <th
                    scope="col"
                    className="py-2.5 pr-4 text-right font-medium"
                  >
                    옵션 / 총 재고
                  </th>
                  <th scope="col" className="py-2.5 pr-4 font-medium">
                    판매 상태
                  </th>
                  <th scope="col" className="py-2.5 font-medium">
                    관리
                  </th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((p) => (
                  <tr key={p.product_id} className="border-cream-300 border-b">
                    <td className="text-brown-600 py-2.5 pr-4">
                      {p.product_id}
                    </td>
                    <td className="py-2.5 pr-4 font-medium">{p.name}</td>
                    <td className="py-2.5 pr-4">{p.origin}</td>
                    <td className="py-2.5 pr-4">
                      {label(ROAST_LEVEL, p.roast_level)}
                    </td>
                    <td className="py-2.5 pr-4 text-right whitespace-nowrap">
                      {formatWon(p.base_price)}
                    </td>
                    <td className="py-2.5 pr-4 text-right whitespace-nowrap">
                      {p.option_count} / {p.total_stock}
                    </td>
                    <td className="py-2.5 pr-4">
                      <StatusBadge
                        type="sales"
                        status={p.sales_status}
                        size="sm"
                      />
                    </td>
                    <td className="py-2.5">
                      <div className="flex gap-2">
                        <Link
                          to={`/admin/products/${p.product_id}`}
                          className={linkButton}
                        >
                          수정
                        </Link>
                        <Button
                          size="sm"
                          variant={
                            p.sales_status === "STOPPED" ? "outline" : "danger"
                          }
                          disabled={busy}
                          onClick={() => toggle(p)}
                        >
                          {p.sales_status === "STOPPED"
                            ? "판매 재개"
                            : "판매 중지"}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination count={result.count} page={page} />
        </>
      )}
    </div>
  );
}

// Remounted per query (key), so the inputs start from the URL.
function FilterForm() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [search, setSearch] = useState(params.get("search") ?? "");
  const [status, setStatus] = useState(params.get("sales_status") ?? "");
  return (
    <form
      className="flex flex-wrap items-end gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        const next = new URLSearchParams();
        if (search.trim()) next.set("search", search.trim());
        if (status) next.set("sales_status", status);
        navigate(
          next.toString() ? `/admin/products?${next}` : "/admin/products",
        );
      }}
    >
      <TextField
        label="원두 이름"
        type="search"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="flex-[0_1_280px]"
      />
      <SelectField
        label="판매 상태"
        options={STATUS_OPTIONS}
        value={status}
        onChange={(e) => setStatus(e.target.value)}
        className="flex-[0_1_160px]"
      />
      <Button type="submit" variant="secondary">
        검색
      </Button>
    </form>
  );
}
