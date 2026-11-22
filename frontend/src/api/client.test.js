import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import client, { setAuthFailureHandler } from "./client";
import { getAccess, getRefresh, setTokens } from "../auth/tokenStore";

// Fake transport: each test lists how the server answers, by URL.
function fakeServer(routes) {
  const calls = [];
  client.defaults.adapter = async (config) => {
    calls.push({
      url: config.url,
      auth: config.headers.Authorization,
      data: config.data,
    });
    const answer = routes[config.url](config, calls);
    const response = {
      data: answer.data ?? {},
      status: answer.status,
      statusText: "",
      headers: {},
      config,
    };
    if (answer.status >= 400) {
      const error = new Error(
        `Request failed with status code ${answer.status}`,
      );
      error.config = config;
      error.response = response;
      error.isAxiosError = true;
      throw error;
    }
    return response;
  };
  return calls;
}

describe("api client", () => {
  let onFailure;
  const originalAdapter = client.defaults.adapter;

  beforeEach(() => {
    onFailure = vi.fn();
    setAuthFailureHandler(onFailure);
  });

  afterEach(() => {
    client.defaults.adapter = originalAdapter;
  });

  it("sends requests under /api", () => {
    expect(client.defaults.baseURL).toBe("/api");
  });

  it("attaches the stored access token", async () => {
    setTokens({ access: "a1", refresh: "r1" });
    const calls = fakeServer({ "/orders/": () => ({ status: 200 }) });
    await client.get("/orders/");
    expect(calls[0].auth).toBe("Bearer a1");
  });

  it("sends no Authorization header when logged out", async () => {
    const calls = fakeServer({ "/products/": () => ({ status: 200 }) });
    await client.get("/products/");
    expect(calls[0].auth).toBeUndefined();
  });

  it("refreshes once on 401 and retries with the new token", async () => {
    setTokens({ access: "old", refresh: "r1" });
    const calls = fakeServer({
      "/orders/": (config) =>
        config.headers.Authorization === "Bearer new"
          ? { status: 200, data: { ok: true } }
          : { status: 401 },
      "/auth/token/refresh/": () => ({ status: 200, data: { access: "new" } }),
    });
    const res = await client.get("/orders/");
    expect(res.data).toEqual({ ok: true });
    expect(getAccess()).toBe("new");
    expect(getRefresh()).toBe("r1");
    expect(calls.map((c) => c.url)).toEqual([
      "/orders/",
      "/auth/token/refresh/",
      "/orders/",
    ]);
    expect(JSON.parse(calls[1].data)).toEqual({ refresh: "r1" });
  });

  it("shares one refresh between requests that fail together", async () => {
    setTokens({ access: "old", refresh: "r1" });
    const calls = fakeServer({
      "/orders/": (config) =>
        config.headers.Authorization === "Bearer new"
          ? { status: 200 }
          : { status: 401 },
      "/cart/": (config) =>
        config.headers.Authorization === "Bearer new"
          ? { status: 200 }
          : { status: 401 },
      "/auth/token/refresh/": () => ({ status: 200, data: { access: "new" } }),
    });
    await Promise.all([client.get("/orders/"), client.get("/cart/")]);
    expect(calls.filter((c) => c.url === "/auth/token/refresh/")).toHaveLength(
      1,
    );
  });

  it("clears tokens and hands over to the login redirect when refresh fails", async () => {
    setTokens({ access: "old", refresh: "expired" });
    fakeServer({
      "/orders/": () => ({ status: 401 }),
      "/auth/token/refresh/": () => ({
        status: 401,
        data: { code: "INVALID_TOKEN" },
      }),
    });
    await expect(client.get("/orders/")).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(getAccess()).toBeNull();
    expect(getRefresh()).toBeNull();
    expect(onFailure).toHaveBeenCalledTimes(1);
  });

  it("does not refresh when the login request itself is rejected", async () => {
    const calls = fakeServer({
      "/auth/token/": () => ({
        status: 401,
        data: { code: "INVALID_CREDENTIALS" },
      }),
    });
    await expect(
      client.post("/auth/token/", { email: "a@b.c", password: "x" }),
    ).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(calls).toHaveLength(1);
    expect(onFailure).not.toHaveBeenCalled();
  });

  it("does not refresh without a stored refresh token", async () => {
    const calls = fakeServer({ "/orders/": () => ({ status: 401 }) });
    await expect(client.get("/orders/")).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(calls).toHaveLength(1);
    expect(onFailure).toHaveBeenCalledTimes(1);
  });
});
