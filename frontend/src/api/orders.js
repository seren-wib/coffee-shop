import client from "./client";

// SDD 4.5. {id} is the order number (order_id).
export async function createOrder(body) {
  const res = await client.post("/orders/", body);
  return res.data;
}

export async function listOrders(params) {
  const res = await client.get("/orders/", { params });
  return res.data;
}

export async function getOrder(orderId) {
  const res = await client.get(`/orders/${orderId}/`);
  return res.data;
}

export async function cancelOrder(orderId) {
  const res = await client.post(`/orders/${orderId}/cancel/`);
  return res.data;
}

export async function requestCancel(orderId, reason) {
  const res = await client.post(`/orders/${orderId}/cancel-request/`, {
    reason,
  });
  return res.data;
}
