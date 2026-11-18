import { describe, expect, it } from "vitest";
import client from "./client";

describe("api client", () => {
  it("sends requests under /api", async () => {
    let seen;
    const res = await client.get("/products/", {
      adapter: async (config) => {
        seen = config;
        return { data: [], status: 200, statusText: "OK", headers: {}, config };
      },
    });
    expect(seen.baseURL).toBe("/api");
    expect(seen.url).toBe("/products/");
    expect(res.status).toBe(200);
  });
});
