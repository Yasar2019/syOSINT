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
  "disputed",
  "false",
];

describe("loadPublicDataset", () => {
  it("loads a bilingual synthetic record for every category and confidence", () => {
    const dataset = loadPublicDataset();
    const presentCategories = new Set(dataset.incidents.flatMap((item) => item.categories));
    const presentConfidence = new Set(dataset.incidents.map((item) => item.confidence));

    expect(dataset.synthetic).toBe(true);
    expect(dataset.incidents.length).toBeGreaterThanOrEqual(6);
    expect([...presentCategories].sort()).toEqual([...categories].sort());
    expect([...presentConfidence].sort()).toEqual([...confidenceLabels].sort());
    expect(dataset.incidents.every((item) => item.title.en.startsWith("[DEMO]"))).toBe(true);
    expect(dataset.incidents.every((item) => item.title.ar.startsWith("[تجريبي]"))).toBe(true);
  });
});
