// The only file that reads or writes the token keys (SDD 4.1.5).
const ACCESS_KEY = "coffee.access";
const REFRESH_KEY = "coffee.refresh";

export function getAccess() {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefresh() {
  return localStorage.getItem(REFRESH_KEY);
}

// The refresh endpoint returns only a new access token, so refresh is optional.
export function setTokens({ access, refresh }) {
  localStorage.setItem(ACCESS_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// The role claim only decides what the screen shows; the server checks the
// role in the database on every admin request (NFR-10).
export function getRole() {
  const access = getAccess();
  if (!access) return null;
  try {
    const part = access.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(part)).role ?? null;
  } catch {
    return null;
  }
}

export function isLoggedIn() {
  return getAccess() !== null;
}
