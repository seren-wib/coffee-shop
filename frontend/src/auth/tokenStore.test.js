import { describe, expect, it } from "vitest";
import {
  clearTokens,
  getAccess,
  getRefresh,
  getRole,
  setTokens,
} from "./tokenStore";
import { makeJwt } from "../test/jwt";

describe("tokenStore", () => {
  it("keeps both tokens under the coffee.* keys", () => {
    setTokens({ access: "a1", refresh: "r1" });
    expect(localStorage.getItem("coffee.access")).toBe("a1");
    expect(localStorage.getItem("coffee.refresh")).toBe("r1");
    expect(getAccess()).toBe("a1");
    expect(getRefresh()).toBe("r1");
  });

  it("keeps the refresh token when only a new access token arrives", () => {
    setTokens({ access: "a1", refresh: "r1" });
    setTokens({ access: "a2" });
    expect(getAccess()).toBe("a2");
    expect(getRefresh()).toBe("r1");
  });

  it("clears both tokens", () => {
    setTokens({ access: "a1", refresh: "r1" });
    clearTokens();
    expect(getAccess()).toBeNull();
    expect(getRefresh()).toBeNull();
  });

  it("reads the role claim from the access token", () => {
    setTokens({ access: makeJwt({ user_id: 1, role: "ADMIN" }), refresh: "r" });
    expect(getRole()).toBe("ADMIN");
  });

  it("returns no role without a token or with a malformed one", () => {
    expect(getRole()).toBeNull();
    setTokens({ access: "not-a-jwt", refresh: "r" });
    expect(getRole()).toBeNull();
  });
});
