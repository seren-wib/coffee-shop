import { ANONYMOUS, loadTossPayments } from "@tosspayments/tosspayments-sdk";
import { startPayment } from "../api/payments";

// pg_order_id is "<order id>-P<n>" (SDD 4.6.1).
export function orderIdFromPgOrderId(pgOrderId) {
  return pgOrderId ? pgOrderId.replace(/-P\d+$/, "") : null;
}

// Starts a payment record, then opens the Toss window (SDD 4.6.2). The browser leaves
// for successUrl or failUrl; closing the window rejects with code USER_CANCEL (SDD 4.6.4).
export async function payOrder(orderId) {
  const payment = await startPayment(orderId);
  const clientKey = import.meta.env.VITE_TOSS_CLIENT_KEY;
  if (!clientKey) {
    const error = new Error("결제창 키가 설정되지 않았습니다.");
    error.code = "NO_CLIENT_KEY";
    throw error;
  }
  const toss = await loadTossPayments(clientKey);
  await toss.payment({ customerKey: ANONYMOUS }).requestPayment({
    method: "CARD",
    amount: { currency: "KRW", value: payment.amount },
    orderId: payment.pg_order_id,
    orderName: payment.order_name,
    customerName: payment.customer_name,
    successUrl: `${window.location.origin}/checkout/result`,
    failUrl: `${window.location.origin}/checkout/result?fail=1`,
  });
}

// Line shown when the window could not be opened or was closed.
export function payErrorMessage(error) {
  if (error?.code === "USER_CANCEL") return "결제를 취소했습니다.";
  if (error?.code === "NO_CLIENT_KEY") return error.message;
  if (!error?.response)
    return "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.";
  return error.response.data?.message || "일시적인 오류가 발생했습니다.";
}
