import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getAdminOrder, runOrderAction } from "../../api/admin";
import AdminTabs from "../../components/AdminTabs";
import Button from "../../components/Button";
import Notice from "../../components/Notice";
import SelectField from "../../components/SelectField";
import StatusBadge from "../../components/StatusBadge";
import TextField from "../../components/TextField";
import { formatDateTime } from "../../lib/date";
import { errorMessage, fieldErrors, isOffline } from "../../lib/errors";
import { formatWon } from "../../lib/format";
import {
  COURIER,
  GRIND_TYPE,
  ORDER_STATUS,
  PAYMENT_METHOD,
  PAYMENT_STATUS,
  WEIGHT_SIZE,
  label,
} from "../../lib/labels";

const PG_CANCEL_FAILED =
  "결제 취소에 실패했습니다. 잠시 후 다시 승인해 주세요.";

// SCR-14 (FR-46 ~ FR-51, UC-13, UC-14). Only the server's allowed_actions get buttons (DR-19).
export default function AdminOrderDetailPage() {
  const { id } = useParams();
  const [loaded, setLoaded] = useState({ id: null, order: null, error: null });
  const [actionError, setActionError] = useState(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(
    () =>
      getAdminOrder(id).then(
        (order) => setLoaded({ id, order, error: null }),
        (error) => setLoaded({ id, order: null, error }),
      ),
    [id],
  );

  useEffect(() => {
    let active = true;
    getAdminOrder(id).then(
      (order) => active && setLoaded({ id, order, error: null }),
      (error) => active && setLoaded({ id, order: null, error }),
    );
    return () => {
      active = false;
    };
  }, [id]);

  // An action is followed by a fresh GET (SDD 6.0.3).
  async function run(action, body) {
    setBusy(true);
    setActionError(null);
    try {
      await runOrderAction(id, action, body);
      await reload();
    } catch (err) {
      setActionError(err);
    }
    setBusy(false);
  }

  const fresh = loaded.id === id;
  const order = fresh ? loaded.order : null;
  const error = fresh ? loaded.error : null;

  if (error) {
    return (
      <Page>
        {error.response?.status === 404 ? (
          <>
            <h1 className="font-serif text-[28px] font-bold">
              주문을 찾을 수 없습니다
            </h1>
            <Link to="/admin/orders">주문 목록으로 가기</Link>
          </>
        ) : (
          <Notice kind={isOffline(error) ? "offline" : "error"}>
            {errorMessage(error)}
          </Notice>
        )}
      </Page>
    );
  }
  if (!order) {
    return (
      <Page>
        <div aria-hidden="true" className="bg-cream-100 h-72 rounded-xl" />
      </Page>
    );
  }

  const actions = order.allowed_actions ?? [];
  const actionMessage =
    actionError?.response?.data?.code === "PG_ERROR"
      ? PG_CANCEL_FAILED
      : errorMessage(actionError);
  const showFormError =
    actionError && Object.keys(fieldErrors(actionError)).length === 0;

  return (
    <Page>
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="font-serif text-[28px] font-bold">
          주문 {order.order_id}
        </h1>
        <StatusBadge status={order.status} />
        <span className="text-brown-600 text-sm">
          {formatDateTime(order.created_at)} · {order.member?.email}
        </span>
      </div>

      {showFormError && actionError && (
        <Notice kind={isOffline(actionError) ? "offline" : "error"}>
          {actionMessage}
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
                      {label(GRIND_TYPE, item.grind_type)} · {item.quantity}개
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
            <SectionTitle>회원·결제 정보</SectionTitle>
            <Details>
              <dt>회원</dt>
              <dd>
                {order.member?.user_name} · {order.member?.email} ·{" "}
                {order.member?.phone_number}
              </dd>
              <dt>최종 결제금액</dt>
              <dd>
                <span className="font-bold">
                  {formatWon(order.final_payment_amt)}
                </span>{" "}
                <span className="text-brown-600">
                  (상품 {formatWon(order.total_product_amt)} + 배송비{" "}
                  {formatWon(order.shipping_fee)})
                </span>
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
                          p.pg_tid ? `거래 ID …${p.pg_tid.slice(-8)}` : null,
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
                  <dd>
                    {order.courier_name} · {order.tracking_number}
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

          {actions.includes("ship") && (
            <ShipForm
              busy={busy}
              error={actionError}
              onShip={(body) => run("ship", body)}
            />
          )}
        </div>

        <aside
          aria-label={
            order.status === "CANCEL_REQUESTED" ? "취소 요청" : "주문 처리"
          }
          className="border-cream-300 flex min-w-[280px] flex-[1_1_320px] flex-col gap-3.5 rounded-xl border p-6"
        >
          <h2 className="text-lg font-bold">
            {order.status === "CANCEL_REQUESTED" ? "취소 요청" : "주문 처리"}
          </h2>
          {order.status === "CANCEL_REQUESTED" && (
            <dl className="[&_dt]:text-brown-600 grid grid-cols-[96px_minmax(0,1fr)] gap-x-3 gap-y-2 text-sm">
              <dt>사유</dt>
              <dd>{order.cancel_reason}</dd>
              <dt>요청 전 상태</dt>
              <dd>{label(ORDER_STATUS, order.status_before_cancel)}</dd>
            </dl>
          )}
          <div className="flex flex-wrap gap-2">
            {actions.includes("prepare") && (
              <Button onClick={() => run("prepare")} disabled={busy}>
                배송 준비
              </Button>
            )}
            {actions.includes("deliver") && (
              <Button onClick={() => run("deliver")} disabled={busy}>
                배송 완료
              </Button>
            )}
            {actions.includes("cancel_approve") && (
              <Button
                variant="danger"
                disabled={busy}
                onClick={() => {
                  if (
                    window.confirm(
                      "취소를 승인할까요? 결제가 취소되고 되돌릴 수 없습니다.",
                    )
                  ) {
                    run("cancel-approve");
                  }
                }}
              >
                취소 승인
              </Button>
            )}
            {actions.includes("cancel_reject") && (
              <Button
                variant="secondary"
                onClick={() => run("cancel-reject")}
                disabled={busy}
              >
                취소 반려
              </Button>
            )}
          </div>
          {actions.includes("ship") && (
            <p className="text-brown-600 text-[13px]">
              왼쪽 배송 처리에서 송장을 등록하세요.
            </p>
          )}
          {actions.length === 0 && (
            <p className="text-brown-600 text-[13px]">
              지금 처리할 동작이 없습니다.
            </p>
          )}
        </aside>
      </div>
    </Page>
  );
}

const COURIER_OPTIONS = Object.entries(COURIER).map(([value, name]) => ({
  value,
  label: name,
}));

function ShipForm({ busy, error, onShip }) {
  const [courier, setCourier] = useState("CJ");
  const [tracking, setTracking] = useState("");
  const errors = fieldErrors(error);
  return (
    <section className="flex flex-col gap-3">
      <SectionTitle>배송 처리</SectionTitle>
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          onShip({ courier_code: courier, tracking_number: tracking.trim() });
        }}
      >
        <SelectField
          label="택배사"
          options={COURIER_OPTIONS}
          value={courier}
          onChange={(e) => setCourier(e.target.value)}
          className="flex-[0_1_200px]"
        />
        <TextField
          label="송장번호"
          required
          inputMode="numeric"
          maxLength={30}
          value={tracking}
          onChange={(e) => setTracking(e.target.value)}
          error={errors.tracking_number ?? errors.courier_code}
          className="flex-[0_1_240px]"
        />
        <Button type="submit" disabled={busy}>
          송장 등록
        </Button>
      </form>
    </section>
  );
}

function Page({ children }) {
  return (
    <div className="flex flex-col gap-6 px-12 pt-8 pb-14">
      <AdminTabs />
      {children}
    </div>
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
