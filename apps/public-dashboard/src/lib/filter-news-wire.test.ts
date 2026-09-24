import { describe, expect, it } from "vitest";
import type { PublicNewsWireEntry } from "@syosint/schemas";
import { filterNewsWire } from "./filter-news-wire";

const entry = (
  id: string,
  sourceId: string,
  language: "en" | "ar",
): PublicNewsWireEntry => ({
  id,
  sourceId,
  sourceLabel: { en: sourceId, ar: sourceId },
  language,
  headline: id,
  url: `https://example.org/${id}`,
  publishedAt: "2026-09-23T16:00:00Z",
  collectedAt: "2026-09-23T16:00:00Z",
});

const entries = [entry("a", "un", "en"), entry("b", "bbc", "ar"), entry("c", "bbc", "en")];

describe("filterNewsWire", () => {
  it("filters sources and languages without mutating input", () => {
    const before = structuredClone(entries);

    expect(
      filterNewsWire(entries, { sourceIds: ["bbc"], languages: ["ar"] }).map(
        (entry) => entry.id,
      ),
    ).toEqual(["b"]);
    expect(entries).toEqual(before);
  });

  it("treats empty filter arrays as all entries", () => {
    expect(filterNewsWire(entries, { sourceIds: [], languages: [] })).toEqual(
      entries,
    );
  });
});
