import { describe, expect, it } from "vitest";

import { formatRange, formatSeconds } from "./time";

describe("time formatting", () => {
  it("formats seconds as timeline labels", () => {
    expect(formatSeconds(0)).toBe("0:00");
    expect(formatSeconds(62.4)).toBe("1:02.4");
  });

  it("formats evidence ranges", () => {
    expect(formatRange(1.5, 4)).toBe("0:01.5 - 0:04");
  });
});
