import { describe, expect, it } from "vitest";
import { loadPublicTelegramWire } from "./load-public-telegram-wire";

const entry = {
  id: "telegram:example:42", status: "active", channel: { name: "Example", username: "example", language: "mixed" },
  url: "https://t.me/example/42", headline: { en: "Reviewed headline", ar: "عنوان مراجع" },
  publishedAt: "2026-09-27T15:00:00Z", approvedAt: "2026-09-27T16:00:00Z", revisions: [],
};
const wire = { schemaVersion: "1.0.0", generatedAt: "2026-09-27T16:00:00Z", lastEditorialUpdateAt: "2026-09-27T16:00:00Z", entries: [entry] };

describe("loadPublicTelegramWire", () => {
  it("validates, orders and retains only the seven-day public window", () => {
    const result = loadPublicTelegramWire({ ...wire, entries: [entry, { ...entry, id: "telegram:example:41", url: "https://t.me/example/41", publishedAt: "2026-09-10T15:00:00Z" }] }, new Date("2026-09-28T12:00:00Z"));
    expect(result.entries.map((item) => item.id)).toEqual([entry.id]);
  });
  it("rejects private fields and invalid links", () => {
    expect(() => loadPublicTelegramWire({ ...wire, entries: [{ ...entry, rawText: "private" }] })).toThrow("Invalid public Telegram wire");
    expect(() => loadPublicTelegramWire({ ...wire, entries: [{ ...entry, url: "https://evil.example/42" }] })).toThrow("Invalid public Telegram wire");
  });
});
