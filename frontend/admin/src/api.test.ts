import { describe, expect, it } from "vitest";

import { bearer, conversationLabel, type Conversation } from "./api";

const base = (over: Partial<Conversation>): Conversation => ({
  id: "1",
  title: null,
  created_at: "",
  updated_at: "",
  ...over,
});

describe("admin api helpers", () => {
  it("formats a bearer header", () => {
    expect(bearer("tok")).toBe("Bearer tok");
  });

  it("labels titled conversations with their title", () => {
    expect(conversationLabel(base({ title: "Lunch booking" }))).toBe("Lunch booking");
  });

  it("falls back for null/blank titles", () => {
    expect(conversationLabel(base({ title: null }))).toBe("(untitled)");
    expect(conversationLabel(base({ title: "   " }))).toBe("(untitled)");
  });
});
