import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

const { apiMock } = vi.hoisted(() => ({ apiMock: vi.fn() }));
vi.mock("../../lib/api", () => ({ api: apiMock }));
vi.mock("../actions", () => ({ resolveTelegramChannel: vi.fn(), approveTelegramChannel: vi.fn(), syncTelegramChannel: vi.fn(), updateTelegramMediaPolicy: vi.fn() }));
vi.mock("next/link", () => ({ default: ({ children, href }: React.PropsWithChildren<{ href: string }>) => <a href={href}>{children}</a> }));

import TelegramPage from "./page";

beforeEach(() => {
  apiMock.mockImplementation((path: string) => {
    if (path === "/telegram/status") return Promise.resolve({ state: "not-configured" });
    if (path === "/telegram/channels") return Promise.resolve([]);
    if (path === "/intake-items?status=new") return Promise.resolve([]);
    throw new Error(`Unexpected path ${path}`);
  });
});

it("explains terminal-only setup without exposing secret fields", async () => {
  render(await TelegramPage({ searchParams: Promise.resolve({}) }));
  expect(screen.getByText("Telegram is not configured")).toBeVisible();
  expect(screen.queryByText(/api_hash|phone|session/i)).toBeNull();
  expect(screen.getByText("Stored locally — never public automatically")).toBeVisible();
});

it("shows resolved identity for an explicit approval and hides raw post HTML", async () => {
  apiMock.mockImplementation((path: string) => {
    if (path === "/telegram/status") return Promise.resolve({ state: "authenticated" });
    if (path === "/telegram/channels") return Promise.resolve([{ id: 1, name: "Public News", username: "publicnews", language: "en", enabled: true, media_enabled: false, status: "healthy" }]);
    if (path === "/intake-items?status=new") return Promise.resolve([{ id: 5, source_id: 1, platform: "telegram", status: "new", text: "<img src=x onerror=alert(1)>", collected_at: "2026-09-27T10:02:00Z" }]);
    throw new Error(`Unexpected path ${path}`);
  });
  render(await TelegramPage({ searchParams: Promise.resolve({ candidate: "publicnews", channel_id: "42", title: "Public News" }) }));
  expect(screen.getByText("Public News", { selector: "strong" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Approve channel for local collection" })).toBeVisible();
  expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeVisible();
  expect(document.querySelector("article img")).toBeNull();
});
