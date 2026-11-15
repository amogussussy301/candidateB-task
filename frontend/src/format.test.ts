import { describe, expect, it } from "vitest";
import { formatDate, formatMoney } from "./format";

describe("formatMoney", () => {
  it("groups rubles without converting exact decimal strings to numbers", () => {
    expect(formatMoney("1234567890123456.01")).toBe("1\u00a0234\u00a0567\u00a0890\u00a0123\u00a0456,01\u00a0₽");
  });

  it("keeps kopecks and uses a typographic minus", () => {
    expect(formatMoney("0.01")).toBe("0,01\u00a0₽");
    expect(formatMoney("-1250.50")).toBe("−1\u00a0250,50\u00a0₽");
  });

  it("rejects malformed values instead of silently rounding them", () => {
    expect(() => formatMoney("12.345")).toThrow("Некорректная денежная сумма");
  });
});

describe("formatDate", () => {
  it("formats an ISO date in Russian without a timezone shift", () => {
    expect(formatDate("2026-11-10")).toBe("10 ноября 2026 г.");
  });
});
