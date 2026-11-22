import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { confirmPayment, failPayment } from "../api/payments";
import Button from "../components/Button";
import Notice from "../components/Notice";
import { errorMessage } from "../lib/errors";
import { formatWon } from "../lib/format";
import { orderIdFromPgOrderId, payErrorMessage, payOrder } from "../lib/pay";

// Payment result (SDD 6.7, FR-26 ~ FR-28). Toss sends the browser here from successUrl or failUrl.
export default function CheckoutResultPage() {
  const [params] = useSearchParams();
  const failed = params.get("fail") === "1";
  const pgOrderId = params.get("orderId");
  const orderId = orderIdFromPgOrderId(pgOrderId);
  const [state, setState] = useState({ phase: "checking" });
  const started = useRef(false);

  const confirm = useCallback(() => {
    confirmPayment({
      paymentKey: params.get("paymentKey"),
      orderId: pgOrderId,
      amount: params.get("amount"),
    }).then(
      (result) => setState({ phase: "done", result }),
      (error) =>
        setState({
          phase: error.response?.data?.code === "PG_ERROR" ? "slow" : "failed",
          message: errorMessage(error),
        }),
    );
  }, [params, pgOrderId]);

  useEffect(() => {
    // Runs once even under StrictMode; the confirm API is idempotent anyway (SDD 4.6.3).
    if (started.current) return;
    started.current = true;
    if (failed) {
      const message = params.get("message") || "결제가 완료되지 않았습니다.";
      failPayment({ orderId: pgOrderId, code: params.get("code"), message })
        .catch(() => {})
        .finally(() => setState({ phase: "failed", message }));
      return;
    }
    confirm();
  }, [confirm, failed, params, pgOrderId]);

  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(420px,1fr))] content-start gap-8 px-12 pt-10 pb-14">
      {state.phase === "checking" && (
        <p role="status" className="text-brown-600 text-[15px]">
          결제를 확인하는 중입니다
        </p>
      )}
      {state.phase === "done" && <Success result={state.result} />}
      {state.phase === "slow" && (
        <ResultCard
          dot="bg-brown-400"
          badge="확인 중"
          title="결제 확인이 늦어지고 있습니다"
        >
          <p className="text-brown-600 text-[15px]">{state.message}</p>
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={() => {
                setState({ phase: "checking" });
                confirm();
              }}
            >
              다시 확인
            </Button>
          </div>
        </ResultCard>
      )}
      {state.phase === "failed" && (
        <Failure orderId={orderId} message={state.message} />
      )}
    </div>
  );
}

function ResultCard({ dot, badge, title, heading: Heading = "h1", children }) {
  return (
    <section className="border-cream-300 flex flex-col gap-5 rounded-xl border p-8">
      <span className="bg-espresso-950 text-latte-100 inline-flex items-center gap-1.5 self-start rounded-sm px-2.5 py-1 text-[13px] font-medium">
        <span aria-hidden="true" className={`size-1.5 rounded-[1px] ${dot}`} />
        {badge}
      </span>
      <Heading className="font-serif text-[32px] font-bold">{title}</Heading>
      {children}
    </section>
  );
}

const linkButton =
  "inline-flex h-8 items-center rounded-md border px-3 text-sm font-medium no-underline";

function Success({ result }) {
  return (
    <ResultCard
      dot="bg-dot-green"
      badge="결제 완료"
      title="결제가 완료되었습니다"
    >
      <dl className="grid grid-cols-[120px_minmax(0,1fr)] gap-x-4 gap-y-2.5 text-[15px]">
        <dt className="text-brown-600">주문번호</dt>
        <dd>{result.order_id}</dd>
        <dt className="text-brown-600">최종 결제금액</dt>
        <dd className="font-bold">{formatWon(result.final_payment_amt)}</dd>
      </dl>
      <div className="flex flex-wrap gap-3">
        <Link
          to={`/orders/${result.order_id}`}
          className={`${linkButton} bg-caramel-700 hover:bg-caramel-800 border-transparent text-white hover:text-white`}
        >
          주문 상세 보기
        </Link>
        <Link
          to="/"
          className={`${linkButton} border-caramel-700 text-caramel-700`}
        >
          원두 더 보기
        </Link>
      </div>
    </ResultCard>
  );
}

function Failure({ orderId, message }) {
  const [pending, setPending] = useState(false);
  const [payError, setPayError] = useState(null);

  async function retry() {
    setPending(true);
    setPayError(null);
    try {
      await payOrder(orderId);
    } catch (err) {
      setPayError(err);
    }
    setPending(false);
  }

  return (
    <ResultCard dot="bg-dot-red" badge="결제 실패" title="결제하지 못했습니다">
      <p className="text-[15px]">{message}</p>
      <p className="text-brown-600 text-sm">
        주문은 결제 대기로 남아 있어서 다시 결제할 수 있습니다.
      </p>
      {orderId && (
        <div className="flex flex-wrap gap-3">
          <Button onClick={retry} disabled={pending}>
            다시 결제
          </Button>
          <Link
            to={`/orders/${orderId}`}
            className={`${linkButton} border-caramel-700 text-caramel-700`}
          >
            주문 상세 보기
          </Link>
        </div>
      )}
      {payError && <Notice>{payErrorMessage(payError)}</Notice>}
    </ResultCard>
  );
}
