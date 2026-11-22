import client from "./client";

// SDD 4.3.1 ~ 4.3.5: page of {product_id, name, origin, roast_level, base_price, lowest_price, image_url, sales_status}.
export async function listProducts(params) {
  const res = await client.get("/products/", { params });
  return res.data;
}

// SDD 4.3.6: product with options [{option_id, weight_size, grind_type, extra_price, price, stock_quantity, is_available}].
export async function getProduct(id) {
  const res = await client.get(`/products/${id}/`);
  return res.data;
}
