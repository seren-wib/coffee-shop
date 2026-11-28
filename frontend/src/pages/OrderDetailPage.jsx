import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { cancelOrder, getOrder, requestCancel } from "../api/orders";
import Button from "../components/Button";
import Notice from "../components/Notice";
import StatusBadge from "../components/StatusBadge";
import { formatDateTime } from "../lib/date";
import { errorMessage, fieldErrors, isOffline } from "../lib/errors";
import { formatWon } from "../lib/format";
import {
  GRIND_TYPE,
  PAYMENT_METHOD,
  PAYMENT_STATUS,
  WEIGHT_SIZE,
  label,
} from "../lib/labels";
import { payErrorMessage, payOrder } from "../lib/pay";

const SHIPPING_STARTED = ["SHIPPED", "DELIVERED"];

// SCR-08 (FR-29, FR-31 ~ FR-35, UC-7 ~ UC-9). Buttons follow the server's can_* values.
export default function OrderDetailPage() {
  const { id } = useParams();
  const [loaded, setLoaded] = useState({ id: null, order: null, error: null });
  const [actionError, setActionError] = useState(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(
    () =>
      getOrder(id).then(
        (order) => setLoaded({ id, order, error: null }),
        (error) => setLoaded({ id, order: null, error }),
      ),
    [id],
  );

  useEffect(() => {
    let active = true;
    getOrder(id).then(
      (order) => active && setLoaded({ id, order, error: null }),
      (error) => active && setLoaded({ id, order: null, error }),
    );
    return () => {
      active = false;
    };
  }, [id]);

  // A change is followed by a fresh GET (SDD 7.0.3).
  async function run(action) {
    setBusy(true);
    setActionError(null);
    try {
      await action();
      await reload();
    } catch (err) {
      setActionError(err);
    }
    setBusy(false);
  }

  const fresh = loaded.id === id;
  const order = fresh ? loaded.order : null;
  const error = fresh ? loaded.error : null;

  if (error?.response?.status === 404) {
    return (
      <div className="flex flex-col gap-3 px-12 pt-10 pb-14">
        <h1 className="font-serif text-[32px] font-bold">
          주문을 찾을 수 없습니다
        </h1>
        <p className="text-[15px]">
          <Link to="/orders">주문 내역으로 가기</Link>
        </p>
      </div>
    );
  }
  if (error) {
    return (
      <div className="px-12 pt-10 pb-14">
        <Notice kind={isOffline(error) ? "offline" : "error"}>
          {errorMessage(error)}
        </Notice>
      </div>
    );
  }
  if (!order) {
    return (
      <div className="px-12 pt-10 pb-14">
        <div aria-hidden="true" className="bg-cream-100 h-72 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 px-12 pt-8 pb-14">
      <nav aria-label="경로" className="text-brown-600 flex gap-2 text-[13px]">
        <Link to="/orders" className="text-brown-600 hover:text-brown-900">
          주문 내역
        </Link>
        <span aria-hidden="true">/</span>
        <span>{order.order_id}</span>
      </nav>

      <div className="flex flex-wrap items-center gap-4">
        <h1 className="font-serif text-[28px] font-bold">
          주문 {order.order_id}
        </h1>
        <StatusBadge status={order.status} />
        <span className="text-brown-600 text-sm">
          {formatDateTime(order.created_at)} 주문
        </span>
      </div>

      {actionError && (
        <Notice kind={isOffline(actionError) ? "offline" : "error"}>
          {actionError.code
            ? payErrorMessage(actionError)
            : errorMessage(actionError)}
        </Notice>
      )}

      <div className="flex flex-wrap items-start gap-8">
        <div className="flex min-w-0 flex-[999_1_560px] flex-col gap-8">
          <section className="flex flex-col gap-3">
            <SectionTitle>주문 상품</SectionTitle>
            <ul>
              {order.items.map((item, index) => (
                <li
                  key={index}
                  className="border-cream-300 flex items-baseline justify-between gap-4 border-b py-2.5 text-sm"
                >
                  <span>
                    <span className="font-medium">{item.product_name}</span>{" "}
                    <span className="text-brown-600">
                      · {label(WEIGHT_SIZE, item.weight_size)} ·{" "}
                      {label(GRIND_TYPE, item.grind_type)} · {item.quantity}개 ·
                      주문 당시 {formatWon(item.order_price)}
                    </span>
                  </span>
                  <span className="whitespace-nowrap">
                    {formatWon(item.subtotal)}
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section className="flex flex-col gap-3">
            <SectionTitle>결제 정보</SectionTitle>
            <Details>
              <dt>상품 금액</dt>
              <dd>{formatWon(order.total_product_amt)}</dd>
              <dt>배송비</dt>
              <dd>{formatWon(order.shipping_fee)}</dd>
              <dt>최종 결제금액</dt>
              <dd className="font-bold">
                {formatWon(order.final_payment_amt)}
              </dd>
              <dt>결제 기록</dt>
              <dd>
                {order.payments.length === 0 ? (
                  "없음"
                ) : (
                  <ul className="flex flex-col gap-1">
                    {order.payments.map((p) => (
                      <li key={p.payment_id}>
                        {[
                          formatDateTime(p.approved_at),
                          p.method ? label(PAYMENT_METHOD, p.method) : null,
                          label(PAYMENT_STATUS, p.status),
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                        {p.failure_reason && (
                          <span className="text-brown-600">
                            {" "}
                            ({p.failure_reason})
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </dd>
            </Details>
          </section>

          <section className="flex flex-col gap-3">
            <SectionTitle>배송 정보</SectionTitle>
            <Details>
              <dt>받는 사람</dt>
              <dd>
                {order.recipient_name} · {order.recipient_phone}
              </dd>
              <dt>주소</dt>
              <dd>{order.shipping_address}</dd>
              {order.courier_name && (
                <>
                  <dt>택배사·송장번호</dt>
                  <dd className="flex flex-wrap gap-3">
                    <span>
                      {order.courier_name} · {order.tracking_number}
                    </span>
                    {order.tracking_url && (
                      <a
                        href={order.tracking_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        배송 조회
                      </a>
                    )}
                  </dd>
                  <dt>배송 완료</dt>
                  <dd>
                    {order.delivered_at
                      ? formatDateTime(order.delivered_at)
                      : "아직 안 됨"}
                  </dd>
                </>
              )}
            </Details>
          </section>
        </div>

        <aside
          aria-label="주문 관리"
          className="border-cream-300 flex min-w-[280px] flex-[1_1_320px] flex-col gap-3.5 rounded-xl border p-6"
        >
          <h2 className="text-lg font-bold">주문 관리</h2>
          <OrderActions
            order={order}
            busy={busy}
            onPay={() => run(() => payOrder(order.order_id))}
            onCancel={() => {
              if (window.confirm("이 주문을 취소할까요? 되돌릴 수 없습니다.")) {
                run(() => cancelOrder(order.order_id));
              }
            }}
            onRequestCancel={(reason) =>
              run(() => requestCancel(order.order_id, reason))
            }
            requestError={actionError}
          />
        </aside>
      </div>
    </div>
  );
}

function OrderActions({
  order,
  busy,
  onPay,
  onCancel,
  onRequestCancel,
  requestError,
}) {
  const [asking, setAsking] = useState(false);
  const [reason, setReason] = useState("");

  if (order.status === "CANCEL_REQUESTED") {
    return (
      <div className="flex flex-col gap-2 text-sm">
        <span className="text-brown-600">취소 사유</span>
        <p>{order.cancel_reason}</p>
        <p className="font-medium">관리자 확인 중</p>
      </div>
    );
  }
  if (order.status === "CANCELLED") {
    return (
      <div className="flex flex-col gap-2 text-sm">
        <p>취소된 주문입니다.</p>
        {order.cancel_reason && (
          <p className="text-brown-600">사유: {order.cancel_reason}</p>
        )}
      </div>
    );
  }
  if (SHIPPING_STARTED.includes(order.status)) {
    return (
      <>
        <Button variant="danger" disabled>
          주문 취소
        </Button>
        <p className="text-brown-600 text-[13px]">
          배송이 시작되어 취소할 수 없습니다.
        </p>
      </>
    );
  }

  const reasonErrors = fieldErrors(requestError).reason;
  return (
    <>
      {order.can_pay && (
        <Button onClick={onPay} disabled={busy}>
          결제하기
        </Button>
      )}
      {order.can_cancel && (
        <Button variant="danger" onClick={onCancel} disabled={busy}>
          주문 취소
        </Button>
      )}
      {order.can_request_cancel && !asking && (
        <Button
          variant="outline"
          onClick={() => setAsking(true)}
          disabled={busy}
        >
          취소 요청
        </Button>
      )}
      {order.can_request_cancel && asking && (
        <form
          className="flex flex-col gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            onRequestCancel(reason.trim());
          }}
        >
          <label htmlFor="cancel-reason" className="text-[13px] font-medium">
            취소 사유
          </label>
          <textarea
            id="cancel-reason"
            required
            maxLength={500}
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className={`focus:border-brown-900 rounded-md border bg-white p-3 text-sm outline-none ${
              reasonErrors ? "border-error" : "border-cream-300"
            }`}
          />
          {reasonErrors && (
            <p className="text-error text-xs">{reasonErrors.join(" ")}</p>
          )}
          <div className="flex gap-2">
            <Button type="submit" variant="outline" disabled={busy}>
              요청 보내기
            </Button>
            <Button variant="ghost" onClick={() => setAsking(false)}>
              닫기
            </Button>
          </div>
        </form>
      )}
    </>
  );
}

function SectionTitle({ children }) {
  return (
    <h2 className="border-brown-900 border-b pb-2.5 text-lg font-bold">
      {children}
    </h2>
  );
}

function Details({ children }) {
  return (
    <dl className="[&_dt]:text-brown-600 grid grid-cols-[140px_minmax(0,1fr)] gap-x-4 gap-y-2.5 text-sm">
      {children}
    </dl>
  );
}
