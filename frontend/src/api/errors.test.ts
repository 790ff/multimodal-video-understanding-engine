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

  it("maps FFmpeg-related processing errors to recovery guidance", () => {
    const message = toUserFacingError(
      new ApiError({
        status: 500,
        code: "audio_extraction_failed",
        message: "ffmpeg stderr with /private/path",
      }),
    );

    expect(message.title).toBe("FFmpeg needs attention");
    expect(message.recovery).toContain("FFmpeg");
    expect(message.message).not.toContain("/private/path");
  });

  it("maps upload size failures without exposing backend details", () => {
    const message = toUserFacingError(
      new ApiError({
        status: 413,
        code: "upload_too_large",
        message: "local max upload stack trace",
      }),
    );

    expect(message.title).toBe("Video is too large");
    expect(message.message).not.toContain("stack");
  });
});
