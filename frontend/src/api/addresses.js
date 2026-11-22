import client from "./client";

// SDD 4.2.1: [{address_id, recipient_name, recipient_phone, zipcode, base_address, detail_address, is_default}].
export async function listAddresses() {
  const res = await client.get("/me/addresses/");
  return res.data;
}
