import client from "./client";

// SDD 4.4.
export async function getCart() {
  const res = await client.get("/cart/");
  return res.data;
}

export async function addCartItem({ optionId, quantity }) {
  const res = await client.post("/cart/items/", {
    option_id: optionId,
    quantity,
  });
  return res.data;
}

export async function updateCartItem(cartItemId, quantity) {
  const res = await client.patch(`/cart/items/${cartItemId}/`, { quantity });
  return res.data;
}

export async function deleteCartItem(cartItemId) {
  await client.delete(`/cart/items/${cartItemId}/`);
}
