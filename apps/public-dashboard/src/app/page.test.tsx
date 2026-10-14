import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PublicNewsWire } from "@syosint/schemas";
import { loadPublicNewsWire } from "../lib/load-public-news-wire";
import HomePage from "./page";

vi.mock("../lib/load-public-news-wire", () => ({ loadPublicNewsWire: vi.fn() }));
vi.mock("../lib/load-public-telegram-wire", () => ({
  loadPublicTelegramWire: () => ({
    schemaVersion: "1.0.0", generatedAt: "2026-10-13T12:00:00Z",
    lastEditorialUpdateAt: "2026-10-13T12:00:00Z", entries: [],
  }),
}));

function syntheticWire(count: number): PublicNewsWire {
  const timestamp = "2026-10-13T12:00:00Z";
  return {
    schemaVersion: "1.1.0", generatedAt: timestamp, lastSuccessfulRefreshAt: timestamp,
    sources: { configured: 1, healthy: 1, delayed: 0 },
    sourceStates: [{ id: "synthetic", label: { en: "Synthetic source", ar: "مصدر تجريبي" },
      language: "en", attribution: "Synthetic attribution", attributionUrl: "https://example.org/legal",
      status: "healthy", lastSuccessfulRefreshAt: timestamp, entryCount: count }],
    entries: Array.from({ length: count }, (_, index) => ({
      id: `synthetic:${index}`, sourceId: "synthetic", sourceLabel: { en: "Synthetic source", ar: "مصدر تجريبي" },
      language: "en", headline: `Synthetic Syria report ${index}`, url: `https://example.org/report-${index}`,
      publishedAt: timestamp, collectedAt: timestamp,
    })),
  };
}

describe("home page composition", () => {
  it.each([0, 2])("renders the complete static dashboard with %i RSS headlines without remote visual assets", (count) => {
    vi.mocked(loadPublicNewsWire).mockReturnValue(syntheticWire(count));
    render(<HomePage />);

    expect(screen.getAllByRole("main")).toHaveLength(1);
    expect(screen.getByText("Demonstration data only")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Syria Situation Desk" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Live News Wire" })).toBeVisible();
    const wire = within(screen.getByRole("region", { name: "Live News Wire" }));
    const disclosures = wire.getAllByText("Unverified external reporting");
    expect(disclosures).toHaveLength(count + 1);
    for (const disclosure of disclosures) expect(disclosure).toBeVisible();
    const cards = wire.queryAllByRole("article");
    expect(cards).toHaveLength(count);
    for (const card of cards) {
      expect(within(card).getByText("Unverified external reporting")).toBeVisible();
    }
    for (let index = 0; index < count; index += 1) {
      expect(wire.getByRole("link", { name: new RegExp(`Synthetic Syria report ${index}`) })).toBeVisible();
    }
    expect(screen.getByRole("region", { name: "Syria situation map" })).toBeVisible();
    expect(screen.getByRole("region", { name: "Activity timeline" })).toBeVisible();
    expect(screen.getByRole("region", { name: "Incident feed" })).toBeVisible();
    expect(screen.getAllByRole("link", { name: "Methodology" }).length).toBeGreaterThan(0);

    for (const element of document.querySelectorAll("img[src], script[src]")) {
      expect(element.getAttribute("src")).not.toMatch(/^https?:/);
    }
  });
});
