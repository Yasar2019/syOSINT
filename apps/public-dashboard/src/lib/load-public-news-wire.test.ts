import { describe, expect, it } from "vitest";
import { loadPublicNewsWire } from "./load-public-news-wire";

const valid = {
  schemaVersion: "1.0.0",
  generatedAt: "2026-09-23T16:00:00Z",
  lastSuccessfulRefreshAt: "2026-09-23T16:00:00Z",
  sources: { healthy: 1, delayed: 0 },
  entries: [
    {
      id: "source:older",
      sourceId: "source",
      sourceLabel: { en: "Source", ar: "المصدر" },
      language: "en",
      headline: "Older Syria report",
      url: "https://example.org/older",
      publishedAt: "2026-09-23T14:00:00Z",
      collectedAt: "2026-09-23T14:01:00Z",
    },
    {
      id: "source:newer",
      sourceId: "source",
      sourceLabel: { en: "Source", ar: "المصدر" },
      language: "ar",
      headline: "خبر أحدث عن سوريا",
      url: "https://example.org/newer",
      publishedAt: "2026-09-23T15:00:00Z",
      collectedAt: "2026-09-23T15:01:00Z",
    },
  ],
} as const;

describe("loadPublicNewsWire", () => {
  it("validates and returns a newest-first copy", () => {
    const input = structuredClone(valid);
    const result = loadPublicNewsWire(input);

    expect(result.entries.map((entry) => entry.id)).toEqual([
      "source:newer",
      "source:older",
    ]);
    expect(input.entries.map((entry) => entry.id)).toEqual([
      "source:older",
      "source:newer",
    ]);
  });

  it("fails closed for private or malformed fields", () => {
    const invalid = structuredClone(valid) as unknown as Record<string, unknown>;
    (invalid.entries as Array<Record<string, unknown>>)[0].body = "private";

    expect(() => loadPublicNewsWire(invalid)).toThrow("Invalid public news wire");
  });
});
