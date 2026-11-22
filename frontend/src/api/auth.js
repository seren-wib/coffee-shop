import client from "./client";

// SDD 4.1.2: returns {access, refresh, user: {user_id, email, user_name, role}}.
export async function login({ email, password }) {
  const res = await client.post("/auth/token/", { email, password });
  return res.data;
}
