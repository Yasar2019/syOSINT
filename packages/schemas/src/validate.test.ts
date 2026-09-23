import { describe, expect, it } from "vitest";
import { validatePublicDataset } from "./validate";

const valid = {
  schemaVersion: "1.0.0",
  generatedAt: "2026-09-22T16:00:00Z",
  synthetic: true,
  incidents: [
    {
      id: "demo-001",
      status: "published",
      categories: ["infrastructure"],
      confidence: "developing",
      occurredAt: "2026-09-22T12:00:00Z",
      updatedAt: "2026-09-22T13:00:00Z",
      location: {
        en: "Synthetic Northern District",
        ar: "منطقة شمالية تجريبية",
        latitude: 35.1,
        longitude: 38.2,
        precision: "governorate",
      },
      title: {
        en: "[DEMO] Infrastructure exercise",
        ar: "[تجريبي] تمرين للبنية التحتية",
      },
      summary: {
        en: "Synthetic demonstration record.",
        ar: "سجل توضيحي تجريبي.",
      },
      uncertainty: {
        en: "No real event is represented.",
        ar: "لا يمثل هذا أي حدث حقيقي.",
      },
      sourceCount: 1,
      sources: [
        {
          id: "demo-source-1",
          label: { en: "Synthetic source", ar: "مصدر تجريبي" },
          url: "https://example.com/demo",
          publishedAt: "2026-09-22T12:00:00Z",
        },
      ],
      corrections: [],
    },
  ],
};

describe("validatePublicDataset", () => {
  it("accepts a complete bilingual synthetic dataset", () => {
    expect(validatePublicDataset(valid)).toEqual({ ok: true, data: valid });
  });

  it("rejects a missing Arabic summary", () => {
    const input = structuredClone(valid);
    delete (input.incidents[0].summary as { ar?: string }).ar;

    expect(validatePublicDataset(input).ok).toBe(false);
  });

  it.each(["rawText", "privateNotes", "telegramSession", "localMediaPath"])(
    "rejects forbidden field %s",
    (field) => {
      const input = structuredClone(valid) as Record<string, unknown>;
      (input.incidents as Array<Record<string, unknown>>)[0][field] = "secret";

      expect(validatePublicDataset(input).ok).toBe(false);
    },
  );

  it("rejects a dataset that is not explicitly synthetic", () => {
    expect(validatePublicDataset({ ...valid, synthetic: false }).ok).toBe(false);
  });

  it("rejects duplicate incident identifiers", () => {
    const input = structuredClone(valid);
    input.incidents.push(structuredClone(input.incidents[0]));

    expect(validatePublicDataset(input)).toEqual({
      ok: false,
      errors: ["incident ids must be unique"],
    });
  });
});
