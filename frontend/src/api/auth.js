import client from "./client";

// SDD 4.1.2: returns {access, refresh, user: {user_id, email, user_name, role}}.
export async function login({ email, password }) {
  const res = await client.post("/auth/token/", { email, password });
  return res.data;
}

// SDD 4.1.1: register; returns {user_id, email, user_name, phone_number, role}.
export async function register(body) {
  const res = await client.post("/auth/register/", body);
  return res.data;
}

// SDD 4.1.7 ~ 4.1.9.
export async function getMe() {
  const res = await client.get("/me/");
  return res.data;
}

export async function updateMe(body) {
  const res = await client.patch("/me/", body);
  return res.data;
}

export async function changePassword({ currentPassword, newPassword }) {
  await client.post("/me/password/", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}
