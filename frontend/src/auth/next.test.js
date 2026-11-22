import { describe, expect, it } from "vitest";
import { safeNext } from "./next";

describe("safeNext", () => {
  it("keeps same-site paths", () => {
    expect(safeNext("/orders")).toBe("/orders");
    expect(safeNext("/?search=에티&page=2")).toBe("/?search=에티&page=2");
  });

  it("falls back to / for anything that could leave the site", () => {
    expect(safeNext(null)).toBe("/");
    expect(safeNext("")).toBe("/");
    expect(safeNext("https://evil.example")).toBe("/");
    expect(safeNext("//evil.example")).toBe("/");
    expect(safeNext("/\\evil.example")).toBe("/");
    expect(safeNext("orders")).toBe("/");
  });
});
