import client from "./client";

// SDD 4.6.2: {payment_id, pg_order_id, amount, order_name, customer_name}.
export async function startPayment(orderId) {
  const res = await client.post(`/orders/${orderId}/payments/`);
  return res.data;
}

// SDD 4.6.3: the values Toss put on successUrl, sent as is.
export async function confirmPayment({ paymentKey, orderId, amount }) {
  const res = await client.post("/payments/confirm/", {
    paymentKey,
    orderId,
    amount: Number(amount),
  });
  return res.data;
}

// SDD 4.6.4: records the failure Toss put on failUrl.
export async function failPayment({ orderId, code, message }) {
  const res = await client.post("/payments/fail/", { orderId, code, message });
  return res.data;
}
