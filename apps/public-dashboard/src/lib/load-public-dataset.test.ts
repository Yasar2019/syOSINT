import { describe, expect, it } from "vitest";
import type { ConfidenceLabel, IncidentCategory } from "@syosint/schemas";
import { loadPublicDataset } from "./load-public-dataset";

const categories: IncidentCategory[] = [
  "armed-conflict",
  "political-security",
  "humanitarian",
  "infrastructure",
  "border-crossing",
  "disinformation",
];

const confidenceLabels: ConfidenceLabel[] = [
  "unverified",
  "developing",
  "corroborated",
  "verified",
  "false",
];

describe("loadPublicDataset", () => {
  it("loads a bilingual synthetic record for every category with a sanitized withdrawal", () => {
    const dataset = loadPublicDataset();
    const presentCategories = new Set(dataset.incidents.flatMap((item) => item.categories));
    const presentConfidence = new Set(dataset.incidents.map((item) => item.confidence));

    const withdrawn = dataset.incidents.find((item) => item.status === "withdrawn");
    expect(withdrawn?.sources).toEqual([]);
    expect(withdrawn?.title.en).toBe("Withdrawn report");
    expect(dataset.synthetic).toBe(true);
    expect(dataset.incidents.length).toBeGreaterThanOrEqual(6);
    expect([...presentCategories].sort()).toEqual([...categories].sort());
    expect([...presentConfidence].sort()).toEqual([...confidenceLabels].sort());
    expect(dataset.incidents.filter((item) => item.status !== "withdrawn").every((item) => item.title.en.startsWith("[DEMO]"))).toBe(true);
    expect(dataset.incidents.filter((item) => item.status !== "withdrawn").every((item) => item.title.ar.startsWith("[تجريبي]"))).toBe(true);
  });

  it.each(["developing", "corroborated", "verified"])(
    "provides two visible demonstration references for %s claims",
    (confidence) => {
      const incident = loadPublicDataset().incidents.find(
        (candidate) => candidate.confidence === confidence,
      );

      expect(incident?.sourceCount).toBe(2);
      expect(incident?.sources).toHaveLength(2);
    },
  );
});
