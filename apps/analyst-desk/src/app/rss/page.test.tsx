import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { apiMock } = vi.hoisted(() => ({ apiMock: vi.fn() }));

vi.mock("../../lib/api", () => ({ api: apiMock }));
vi.mock("../actions", () => ({
  addFeed: vi.fn(),
  attachFeedItem: vi.fn(),
  collectFeed: vi.fn(),
  promoteFeedItem: vi.fn(),
}));
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={String(href)} {...props}>{children}</a>
  ),
}));

import RssInbox from "./page";

const item = (id: number, status: string) => ({
  id,
  source_id: 1,
  status,
  headline: `${status} Syria report ${id}`,
  url: `https://example.org/${id}`,
  text: `Private source text ${id}`,
  published_at: "2026-09-23T15:55:00Z",
  collected_at: "2026-09-23T16:00:00Z",
  incident_id: status === "promoted" ? 7 : null,
});

describe("RSS inbox", () => {
  beforeEach(() => {
    apiMock.mockImplementation((path: string) => {
      if (path === "/feeds") return Promise.resolve([{
        id: 1,
        name: "Example feed",
        url: "https://example.org",
        feed_url: "https://example.org/rss.xml",
        language: "en",
        enabled: true,
        poll_interval_minutes: 30,
        health: {
          status: "healthy",
          last_success_at: "2026-09-23T16:00:00Z",
          consecutive_failures: 0,
          last_error_category: null,
        },
      }]);
      const status = new URL(`http://local${path}`).searchParams.get("status");
      if (status === "new") return Promise.resolve([item(1, "new"), item(2, "new")]);
      if (status === "promoted") return Promise.resolve([item(3, "promoted")]);
      if (status === "attached") return Promise.resolve([]);
      if (status === "duplicate") return Promise.resolve([item(4, "duplicate")]);
      if (status === "quarantined") return Promise.resolve([{
        id: 5,
        source_id: 1,
        status: "quarantined",
        headline: "Future Syria report",
        reason: "future-published-at",
        collected_at: "2026-09-23T16:00:00Z",
      }]);
      throw new Error(`Unexpected path: ${path}`);
    });
  });

  it("separates private collection states and requires human promotion fields", async () => {
    render(await RssInbox({ searchParams: Promise.resolve({}) }));

    expect(screen.getByRole("heading", { name: "RSS inbox" })).toBeTruthy();
    expect(screen.getAllByText("New · 2").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Promoted · 1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Duplicate · 1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Quarantined · 1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Stored locally — never public automatically").length).toBe(2);
    expect(screen.getAllByLabelText("Analyst English title")[0].hasAttribute("required")).toBe(true);
    expect(screen.getAllByLabelText("العنوان الذي كتبه المحلل")[0].hasAttribute("required")).toBe(true);
    expect(screen.getByText("future-published-at")).toBeTruthy();
  });
});
