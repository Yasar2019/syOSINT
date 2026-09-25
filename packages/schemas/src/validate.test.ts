import { describe, expect, it } from "vitest";
import { validatePublicDataset, validatePublicNewsWire } from "./validate";

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

const validWire = {
  schemaVersion: "1.1.0",
  generatedAt: "2026-09-23T16:00:00Z",
  lastSuccessfulRefreshAt: "2026-09-23T16:00:00Z",
  sources: { configured: 2, healthy: 2, delayed: 0 },
  sourceStates: [
    {
      id: "bbc-arabic",
      label: { en: "BBC Arabic", ar: "بي بي سي عربي" },
      language: "ar",
      attribution: "BBC feed attribution",
      attributionUrl: "https://www.bbc.com/legal",
      status: "healthy",
      lastSuccessfulRefreshAt: "2026-09-23T16:00:00Z",
      entryCount: 1,
    },
    {
      id: "empty-source",
      label: { en: "Empty Source", ar: "مصدر فارغ" },
      language: "en",
      attribution: "Empty source attribution",
      attributionUrl: "https://empty.example/legal",
      status: "not-modified",
      lastSuccessfulRefreshAt: null,
      entryCount: 0,
    },
  ],
  entries: [
    {
      id: "bbc-arabic:abc123",
      sourceId: "bbc-arabic",
      sourceLabel: { en: "BBC Arabic", ar: "بي بي سي عربي" },
      language: "ar",
      headline: "خبر تجريبي عن سوريا",
      url: "https://www.bbc.com/arabic/articles/example",
      publishedAt: "2026-09-23T15:55:00Z",
      collectedAt: "2026-09-23T16:00:00Z",
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

  it("accepts a gated production dataset while keeping synthetic fixtures labeled", () => {
    expect(validatePublicDataset({ ...valid, synthetic: false }).ok).toBe(true);
  });

  it("rejects duplicate incident identifiers", () => {
    const input = structuredClone(valid);
    input.incidents.push(structuredClone(input.incidents[0]));

    expect(validatePublicDataset(input)).toEqual({
      ok: false,
      errors: ["incident ids must be unique"],
    });
  });

  it.each(["country", "withheld"])(
    "rejects coordinates when public precision is %s",
    (precision) => {
      const input = structuredClone(valid);
      input.incidents[0].location.precision = precision;

      expect(validatePublicDataset(input).ok).toBe(false);
    },
  );

  it("rejects an incomplete coordinate pair", () => {
    const input = structuredClone(valid);
    delete (input.incidents[0].location as { longitude?: number }).longitude;

    expect(validatePublicDataset(input).ok).toBe(false);
  });

  it("rejects a source count smaller than the public references", () => {
    const input = structuredClone(valid);
    input.incidents[0].sources.push({
      ...structuredClone(input.incidents[0].sources[0]),
      id: "demo-source-2",
      url: "https://example.com/demo-2",
    });

    expect(validatePublicDataset(input)).toEqual({
      ok: false,
      errors: ["incident demo-001 sourceCount cannot be smaller than sources.length"],
    });
  });
});

describe("validatePublicNewsWire", () => {
  it("accepts the bounded public news-wire contract", () => {
    expect(validatePublicNewsWire(validWire)).toEqual({
      ok: true,
      data: validWire,
    });
  });

  it("rejects duplicate ids", () => {
    const duplicate = {
      ...validWire,
      entries: [validWire.entries[0], validWire.entries[0]],
    };

    expect(validatePublicNewsWire(duplicate).ok).toBe(false);
  });

  it("rejects private fields", () => {
    const privateEntry = {
      ...validWire,
      entries: [{ ...validWire.entries[0], body: "private" }],
    };

    expect(validatePublicNewsWire(privateEntry).ok).toBe(false);
  });

  it.each(["error", "exception", "responseBody", "feedUrl", "lastError"])(
    "rejects source state detail %s",
    (field) => {
      const input = structuredClone(validWire) as any;
      input.sourceStates[0][field] = "socket trace";
      expect(validatePublicNewsWire(input).ok).toBe(false);
    },
  );

  it("rejects unknown source counter fields", () => {
    const input = structuredClone(validWire) as any;
    input.sources.lastError = "trace";
    expect(validatePublicNewsWire(input).ok).toBe(false);
  });

  it("rejects unknown source label fields", () => {
    const input = structuredClone(validWire) as any;
    input.sourceStates[0].label.privateNotes = "private";
    expect(validatePublicNewsWire(input).ok).toBe(false);
  });

  it("requires one source state list and configured count", () => {
    const missingStates = structuredClone(validWire) as any;
    delete missingStates.sourceStates;
    const missingCount = structuredClone(validWire) as any;
    delete missingCount.sources.configured;
    expect(validatePublicNewsWire(missingStates).ok).toBe(false);
    expect(validatePublicNewsWire(missingCount).ok).toBe(false);
  });

  it("rejects invalid source state values", () => {
    const invalidStatus = structuredClone(validWire) as any;
    invalidStatus.sourceStates[0].status = "failed: timeout";
    const invalidCount = structuredClone(validWire) as any;
    invalidCount.sourceStates[0].entryCount = -1;
    const invalidRefresh = structuredClone(validWire) as any;
    invalidRefresh.sourceStates[0].lastSuccessfulRefreshAt = "internal trace";
    expect(validatePublicNewsWire(invalidStatus).ok).toBe(false);
    expect(validatePublicNewsWire(invalidCount).ok).toBe(false);
    expect(validatePublicNewsWire(invalidRefresh).ok).toBe(false);
  });

  it("rejects duplicate source state ids", () => {
    const input = structuredClone(validWire);
    input.sourceStates[1].id = input.sourceStates[0].id;
    expect(validatePublicNewsWire(input)).toEqual({
      ok: false,
      errors: ["news-wire source-state ids must be unique"],
    });
  });

  it("rejects entries whose source has no attributed source state", () => {
    const input = structuredClone(validWire);
    input.entries[0].sourceId = "missing-source";

    expect(validatePublicNewsWire(input)).toEqual({
      ok: false,
      errors: ["news-wire entries must reference an attributed source state"],
    });
  });

  it("rejects missing or unsafe attribution links", () => {
    const missing = structuredClone(validWire) as any;
    delete missing.sourceStates[0].attributionUrl;
    const unsafe = structuredClone(validWire);
    unsafe.sourceStates[0].attributionUrl = "http://example.org/legal";

    expect(validatePublicNewsWire(missing).ok).toBe(false);
    expect(validatePublicNewsWire(unsafe).ok).toBe(false);
  });
});
