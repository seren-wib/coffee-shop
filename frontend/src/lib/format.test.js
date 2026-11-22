import { describe, expect, it } from "vitest";
import { formatWon } from "./format";

describe("formatWon", () => {
  it("formats with thousands separators and 원 (NFR-33)", () => {
    expect(formatWon(29000)).toBe("29,000원");
    expect(formatWon(0)).toBe("0원");
    expect(formatWon(1234567)).toBe("1,234,567원");
  });
});
