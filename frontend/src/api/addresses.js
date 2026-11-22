import client from "./client";

// SDD 4.2.1: [{address_id, recipient_name, recipient_phone, zipcode, base_address, detail_address, is_default}].
export async function listAddresses() {
  const res = await client.get("/me/addresses/");
  return res.data;
}

// SDD 4.2.2 ~ 4.2.5.
export async function createAddress(body) {
  const res = await client.post("/me/addresses/", body);
  return res.data;
}

export async function updateAddress(addressId, body) {
  const res = await client.patch(`/me/addresses/${addressId}/`, body);
  return res.data;
}

export async function deleteAddress(addressId) {
  await client.delete(`/me/addresses/${addressId}/`);
}

export async function setDefaultAddress(addressId) {
  const res = await client.post(`/me/addresses/${addressId}/default/`);
  return res.data;
}
