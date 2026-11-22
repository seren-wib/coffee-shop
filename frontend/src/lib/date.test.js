import { describe, expect, it } from "vitest";
import { formatDate, formatDateTime } from "./date";

describe("date format", () => {
  it("shows Seoul time whatever the offset in the string", () => {
    expect(formatDateTime("2026-11-20T14:03:11+09:00")).toBe(
      "2026-11-20 14:03",
    );
    expect(formatDateTime("2026-11-20T15:30:00Z")).toBe("2026-11-21 00:30");
    expect(formatDate("2026-11-20T15:30:00Z")).toBe("2026-11-21");
  });

  it("shows nothing for a missing date", () => {
    expect(formatDateTime(null)).toBe("");
  });
});
