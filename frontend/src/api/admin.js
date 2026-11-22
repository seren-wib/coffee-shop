import client from "./client";

// SDD 4.7 (admin products).
export async function listAdminProducts(params) {
  const res = await client.get("/admin/products/", { params });
  return res.data;
}

export async function getAdminProduct(id) {
  const res = await client.get(`/admin/products/${id}/`);
  return res.data;
}

export async function createProduct(body) {
  const res = await client.post("/admin/products/", body);
  return res.data;
}

export async function updateProduct(id, body) {
  const res = await client.patch(`/admin/products/${id}/`, body);
  return res.data;
}

export async function addOption(id, body) {
  const res = await client.post(`/admin/products/${id}/options/`, body);
  return res.data;
}

// extra_price (FR-40) and stock_quantity (FR-41) share one path.
export async function updateOption(id, optionId, body) {
  const res = await client.patch(
    `/admin/products/${id}/options/${optionId}/`,
    body,
  );
  return res.data;
}

export async function stopSales(id) {
  const res = await client.post(`/admin/products/${id}/stop/`);
  return res.data;
}

export async function resumeSales(id) {
  const res = await client.post(`/admin/products/${id}/resume/`);
  return res.data;
}

// SDD 4.8 (admin orders).
export async function listAdminOrders(params) {
  const res = await client.get("/admin/orders/", { params });
  return res.data;
}

export async function getAdminOrder(orderId) {
  const res = await client.get(`/admin/orders/${orderId}/`);
  return res.data;
}

// action: prepare | ship | deliver | cancel-approve | cancel-reject
export async function runOrderAction(orderId, action, body) {
  const res = await client.post(`/admin/orders/${orderId}/${action}/`, body);
  return res.data;
}
