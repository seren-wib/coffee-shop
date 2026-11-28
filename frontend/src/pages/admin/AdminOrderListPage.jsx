import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { listAdminOrders } from "../../api/admin";
import AdminTabs from "../../components/AdminTabs";
import Button from "../../components/Button";
import Notice from "../../components/Notice";
import Pagination from "../../components/Pagination";
import StatusBadge from "../../components/StatusBadge";
import Tabs from "../../components/Tabs";
import TextField from "../../components/TextField";
import { formatDate } from "../../lib/date";
import { errorMessage, isOffline } from "../../lib/errors";
import { formatWon } from "../../lib/format";
import { ORDER_STATUS } from "../../lib/labels";

// SCR-13 (FR-44, FR-45, FR-57). Search, status tab and page live in the URL.
export default function AdminOrderListPage() {
  const [params] = useSearchParams();
  const query = params.toString();
  const status = params.get("status") ?? "";
  const page = Number(params.get("page")) || 1;
  const [loaded, setLoaded] = useState({
    query: null,
    data: null,
    error: null,
  });
  const [cancelCount, setCancelCount] = useState(0);

  useEffect(() => {
    let active = true;
    const current = new URLSearchParams(query);
    const apiParams = {};
    for (const key of ["status", "search", "page"]) {
      if (current.get(key)) apiParams[key] = current.get(key);
    }
    listAdminOrders(apiParams).then(
      (data) => active && setLoaded({ query, data, error: null }),
      (error) => active && setLoaded({ query, data: null, error }),
    );
    return () => {
      active = false;
    };
  }, [query]);

  // The cancel request tab carries a count badge (SDD 7.14), read once when the screen opens.
  useEffect(() => {
    let active = true;
    listAdminOrders({ status: "CANCEL_REQUESTED" }).then(
      (data) => active && setCancelCount(data.count),
      () => {},
    );
    return () => {
      active = false;
    };
  }, []);

  const fresh = loaded.query === query;
  const result = fresh ? loaded.data : null;
  const error = fresh ? loaded.error : null;

  const tabHref = (code) => {
    const next = new URLSearchParams();
    if (params.get("search")) next.set("search", params.get("search"));
    if (code) next.set("status", code);
    return next.toString() ? `/admin/orders?${next}` : "/admin/orders";
  };

  const tabs = [
    { key: "", to: tabHref(""), label: "전체", current: status === "" },
    ...Object.entries(ORDER_STATUS).map(([code, name]) => ({
      key: code,
      to: tabHref(code),
      label: name,
      current: status === code,
      count: code === "CANCEL_REQUESTED" ? cancelCount : 0,
    })),
  ];

  return (
    <div className="flex flex-col gap-6 px-12 pt-8 pb-14">
      <h1 className="sr-only">주문 관리</h1>
      <AdminTabs />
      <SearchForm
        key={params.get("search") ?? ""}
        initial={params.get("search") ?? ""}
      />
      <Tabs label="주문 상태" items={tabs} />

      {error && (
        <Notice kind={isOffline(error) ? "offline" : "error"}>
          {errorMessage(error)}
        </Notice>
      )}
      {!result && !error && (
        <div aria-hidden="true" className="bg-cream-100 h-60 rounded-xl" />
      )}
      {result?.results.length === 0 && (
        <p className="text-brown-600 py-16 text-center text-[15px]">
          조건에 맞는 주문이 없습니다
        </p>
      )}
      {result?.results.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-brown-900 text-brown-600 border-b text-[13px]">
                  <th scope="col" className="py-2.5 pr-4 font-medium">
                    주문번호
                  </th>
                  <th scope="col" className="py-2.5 pr-4 font-medium">
                    주문일
                  </th>
                  <th scope="col" className="py-2.5 pr-4 font-medium">
                    회원
                  </th>
                  <th
                    scope="col"
                    className="py-2.5 pr-4 text-right font-medium"
                  >
                    결제금액
                  </th>
                  <th scope="col" className="py-2.5 pr-4 font-medium">
                    주문 상태
                  </th>
                  <th scope="col" className="py-2.5">
                    <span className="sr-only">상세</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((o) => (
                  <tr key={o.order_id} className="border-cream-300 border-b">
                    <td className="py-3 pr-4 font-medium whitespace-nowrap">
                      {o.order_id}
                    </td>
                    <td className="py-3 pr-4 whitespace-nowrap">
                      {formatDate(o.created_at)}
                    </td>
                    <td className="py-3 pr-4">{o.member_email}</td>
                    <td className="py-3 pr-4 text-right font-bold whitespace-nowrap">
                      {formatWon(o.final_payment_amt)}
                    </td>
                    <td className="py-3 pr-4">
                      <StatusBadge status={o.status} size="sm" />
                    </td>
                    <td className="py-3 text-right">
                      <Link to={`/admin/orders/${o.order_id}`}>상세</Link>
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

// Remounted per search value (key), so the input starts from the URL.
function SearchForm({ initial }) {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [search, setSearch] = useState(initial);
  return (
    <form
      className="flex flex-wrap items-end gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        const next = new URLSearchParams();
        if (params.get("status")) next.set("status", params.get("status"));
        if (search.trim()) next.set("search", search.trim());
        navigate(next.toString() ? `/admin/orders?${next}` : "/admin/orders");
      }}
    >
      <TextField
        label="주문번호 또는 회원 이메일"
        type="search"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="flex-[0_1_360px]"
      />
      <Button type="submit">검색</Button>
    </form>
  );
}
