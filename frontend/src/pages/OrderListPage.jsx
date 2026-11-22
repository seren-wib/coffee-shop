import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { listOrders } from "../api/orders";
import Notice from "../components/Notice";
import Pagination from "../components/Pagination";
import StatusBadge from "../components/StatusBadge";
import Tabs from "../components/Tabs";
import { formatDate } from "../lib/date";
import { errorMessage, isOffline } from "../lib/errors";
import { formatWon } from "../lib/format";
import { ORDER_STATUS } from "../lib/labels";

// SCR-07 (FR-30, FR-55, UC-7). The status tab and page live in the URL.
export default function OrderListPage() {
  const [params] = useSearchParams();
  const query = params.toString();
  const status = params.get("status") ?? "";
  const page = Number(params.get("page")) || 1;
  const [loaded, setLoaded] = useState({
    query: null,
    data: null,
    error: null,
  });

  useEffect(() => {
    let active = true;
    const current = new URLSearchParams(query);
    const apiParams = {};
    for (const key of ["status", "page"]) {
      if (current.get(key)) apiParams[key] = current.get(key);
    }
    listOrders(apiParams).then(
      (data) => active && setLoaded({ query, data, error: null }),
      (error) => active && setLoaded({ query, data: null, error }),
    );
    return () => {
      active = false;
    };
  }, [query]);

  const fresh = loaded.query === query;
  const result = fresh ? loaded.data : null;
  const error = fresh ? loaded.error : null;

  const tabs = [
    { key: "", to: "/orders", label: "전체", current: status === "" },
    ...Object.entries(ORDER_STATUS).map(([code, name]) => ({
      key: code,
      to: `/orders?status=${code}`,
      label: name,
      current: status === code,
    })),
  ];

  return (
    <div className="flex flex-col gap-6 px-12 pt-10 pb-14">
      <h1 className="font-serif text-[32px] font-bold">주문 내역</h1>
      <Tabs label="주문 상태" items={tabs} />

      {error && (
        <Notice kind={isOffline(error) ? "offline" : "error"}>
          {errorMessage(error)}
        </Notice>
      )}
      {!result && !error && (
        <div aria-hidden="true" className="bg-cream-100 h-60 rounded-xl" />
      )}

      {result && result.results.length === 0 && (
        <p className="text-brown-600 py-16 text-center text-[15px]">
          주문 내역이 없습니다
        </p>
      )}

      {result && result.results.length > 0 && (
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
                    상품
                  </th>
                  <th
                    scope="col"
                    className="py-2.5 pr-4 text-right font-medium"
                  >
                    결제금액
                  </th>
                  <th scope="col" className="py-2.5 pr-4 font-medium">
                    상태
                  </th>
                  <th scope="col" className="py-2.5">
                    <span className="sr-only">상세</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((order) => (
                  <tr
                    key={order.order_id}
                    className="border-cream-300 border-b"
                  >
                    <td className="py-3.5 pr-4 font-medium whitespace-nowrap">
                      {order.order_id}
                    </td>
                    <td className="py-3.5 pr-4 whitespace-nowrap">
                      {formatDate(order.created_at)}
                    </td>
                    <td className="py-3.5 pr-4">
                      {order.item_count > 1
                        ? `${order.first_item_name} 외 ${order.item_count - 1}건`
                        : order.first_item_name}
                    </td>
                    <td className="py-3.5 pr-4 text-right font-bold whitespace-nowrap">
                      {formatWon(order.final_payment_amt)}
                    </td>
                    <td className="py-3.5 pr-4">
                      <StatusBadge status={order.status} size="sm" />
                    </td>
                    <td className="py-3.5 text-right">
                      <Link to={`/orders/${order.order_id}`}>상세보기</Link>
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
