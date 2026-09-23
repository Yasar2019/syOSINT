import { describe, expect, it } from "vitest";
import { countByConfidence, filterIncidents } from "./filter-incidents";
import { loadPublicDataset } from "./load-public-dataset";

const incidents = loadPublicDataset().incidents;

describe("filterIncidents", () => {
  it("combines category, confidence, and bilingual search filters", () => {
    const result = filterIncidents(incidents, {
      categories: ["infrastructure"],
      confidence: ["developing"],
      search: "تجريبي",
    });

    expect(result).toHaveLength(1);
    expect(result[0].categories).toContain("infrastructure");
    expect(result[0].confidence).toBe("developing");
  });

  it("sorts newest occurrence first without mutating input", () => {
    const before = incidents.map((item) => item.id);
    const result = filterIncidents(incidents, {
      categories: [],
      confidence: [],
      search: "",
    });

    expect(incidents.map((item) => item.id)).toEqual(before);
    expect(Date.parse(result[0].occurredAt)).toBeGreaterThanOrEqual(
      Date.parse(result.at(-1)!.occurredAt),
    );
  });

  it("returns no records for an unmatched query", () => {
    expect(
      filterIncidents(incidents, {
        categories: [],
        confidence: [],
        search: "no-such-synthetic-record",
      }),
    ).toEqual([]);
  });

  it("counts every confidence label without dropping zero-value labels", () => {
    expect(countByConfidence(incidents)).toEqual({
      unverified: 1,
      developing: 1,
      corroborated: 1,
      verified: 1,
      disputed: 1,
      false: 1,
    });
  });
});
