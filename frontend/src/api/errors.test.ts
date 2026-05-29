import { describe, expect, it } from "vitest";

import { ApiError } from "./client";
import { toUserFacingError } from "./errors";

describe("toUserFacingError", () => {
  it("maps offline fetch failures to a backend offline message", () => {
    const message = toUserFacingError(
      new ApiError({
        status: 0,
        code: "backend_offline",
        message: "fetch failed",
      }),
    );

    expect(message.title).toBe("Backend offline");
  });

  it("maps provider configuration errors without exposing backend details", () => {
    const message = toUserFacingError(
      new ApiError({
        status: 500,
        code: "frame_analysis_not_configured",
        message: "secret provider detail",
      }),
    );

    expect(message.title).toBe("Provider configuration needed");
    expect(message.message).not.toContain("secret");
  });
});
