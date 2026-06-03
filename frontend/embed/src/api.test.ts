import { describe, expect, it } from "vitest";

import { bearer, isSendable } from "./api";

describe("embed api helpers", () => {
  it("formats a bearer header", () => {
    expect(bearer("abc")).toBe("Bearer abc");
  });

  it("treats whitespace-only drafts as not sendable", () => {
    expect(isSendable("   ")).toBe(false);
    expect(isSendable("")).toBe(false);
  });

  it("treats non-empty drafts as sendable", () => {
    expect(isSendable("hello")).toBe(true);
    expect(isSendable("  hi  ")).toBe(true);
  });
});
