import axios from "axios";
import { loginPath } from "../auth/next";
import {
  clearTokens,
  getAccess,
  getRefresh,
  setTokens,
} from "../auth/tokenStore";

// The only axios instance in the app (NFR-31). Token attach and refresh live here (SDD 4.1.4).
const client = axios.create({
  baseURL: "/api",
});

const NO_REFRESH_URLS = ["/auth/token/", "/auth/token/refresh/"];

let onAuthFailure = () => {
  window.location.assign(
    loginPath(window.location.pathname + window.location.search),
  );
};

// Lets the router (and tests) replace the full-page redirect.
export function setAuthFailureHandler(handler) {
  onAuthFailure = handler;
}

// One refresh in flight at a time; requests that fail together wait on it.
let refreshing = null;

function refreshAccess() {
  if (!refreshing) {
    refreshing = client
      .post(
        "/auth/token/refresh/",
        { refresh: getRefresh() },
        { _retried: true },
      )
      .then((res) => {
        setTokens({ access: res.data.access });
        return res.data.access;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

client.interceptors.request.use((config) => {
  const access = getAccess();
  if (access && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${access}`;
  }
  return config;
});

client.interceptors.response.use(undefined, async (error) => {
  const config = error.config;
  if (
    error.response?.status !== 401 ||
    !config ||
    config._retried ||
    NO_REFRESH_URLS.includes(config.url)
  ) {
    throw error;
  }
  if (!getRefresh()) {
    clearTokens();
    onAuthFailure();
    throw error;
  }
  let access;
  try {
    access = await refreshAccess();
  } catch {
    clearTokens();
    onAuthFailure();
    throw error;
  }
  config._retried = true;
  config.headers.Authorization = `Bearer ${access}`;
  return client(config);
});

export default client;
