import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

const { apiMock } = vi.hoisted(() => ({ apiMock: vi.fn() }));
vi.mock("../../lib/api", () => ({ api: apiMock }));
vi.mock("../actions", () => ({ promoteIntakeItem: vi.fn(), attachIntakeItem: vi.fn() }));
vi.mock("next/link", () => ({ default: ({ children, href }: React.PropsWithChildren<{ href: string }>) => <a href={href}>{children}</a> }));

import IntakePage from "./page";

beforeEach(() => {
  apiMock.mockImplementation((path: string) => {
    if (path === "/sources") return Promise.resolve([{ id: 1, name: "Example source", language: "en" }]);
    if (path === "/intake-items?status=new") return Promise.resolve([
      { id: 2, source_id: 1, platform: "telegram", status: "new", headline: null,
        text: "<img src=x onerror=alert(1)>", url: "https://t.me/publicnews/2",
        published_at: "2026-09-27T10:00:00Z", collected_at: "2026-09-27T10:02:00Z" },
      { id: 3, source_id: 1, platform: "rss", status: "new", headline: "RSS item",
        text: "RSS text", url: "https://example.org/3",
        published_at: "2026-09-27T10:00:00Z", collected_at: "2026-09-27T10:02:00Z" },
    ]);
    if (path.startsWith("/intake-items?status=")) return Promise.resolve([]);
    throw new Error(`Unexpected path ${path}`);
  });
});

it("filters the unified queue and renders Telegram content as plain text", async () => {
  render(await IntakePage({ searchParams: Promise.resolve({ platform: "telegram", status: "new" }) }));
  expect(screen.getByRole("option", { name: "Telegram" })).toBeVisible();
  expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeVisible();
  expect(document.querySelector("article img")).toBeNull();
  expect(screen.getByText("Stored locally — never public automatically")).toBeVisible();
  expect(screen.queryByText("RSS item")).toBeNull();
  expect(screen.getByLabelText("Analyst English title")).toBeVisible();
});

it("shows a safe message when the local API is offline", async () => {
  apiMock.mockRejectedValueOnce(new Error("synthetic secret"));
  render(await IntakePage({ searchParams: Promise.resolve({}) }));
  expect(screen.getByRole("alert")).toHaveTextContent("Local API unavailable");
  expect(screen.queryByText("synthetic secret")).toBeNull();
});
