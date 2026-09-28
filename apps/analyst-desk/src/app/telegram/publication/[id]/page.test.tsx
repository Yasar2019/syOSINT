import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

const { apiMock } = vi.hoisted(() => ({ apiMock: vi.fn() }));
vi.mock("../../../../lib/api", () => ({ api: apiMock }));
vi.mock("../../../actions", () => ({
  previewTelegramPublication: vi.fn(), approveTelegramPublication: vi.fn(),
  correctTelegramPublication: vi.fn(), withdrawTelegramPublication: vi.fn(),
}));
vi.mock("next/link", () => ({ default: ({ children, href }: React.PropsWithChildren<{ href: string }>) => <a href={href}>{children}</a> }));

import PublicationPage from "./page";

const hash = "a".repeat(64);
const record = {
  id: "telegram:42:7", status: "active", channel: { name: "Public Channel", username: "publicnews", language: "ar" },
  url: "https://t.me/publicnews/7", headline: { en: "Analyst headline", ar: "عنوان المحلل" },
  publishedAt: "2026-09-27T15:00:00Z", approvedAt: "2026-09-27T16:00:00Z", revisions: [],
};

beforeEach(() => {
  apiMock.mockImplementation((path: string) => {
    if (path === "/intake-items/7/publication") return Promise.reject(new Error("Publication unavailable"));
    if (path === `/telegram-publication-previews/${hash}`) return Promise.resolve({ item_id: 7, draft_hash: hash, record });
    throw new Error(`Unexpected path ${path}`);
  });
});

it("requires bilingual analyst text and explicit checks for a private preview", async () => {
  render(await PublicationPage({ params: Promise.resolve({ id: "7" }), searchParams: Promise.resolve({}) }));
  expect(screen.getByText("Original Telegram text stays private")).toBeTruthy();
  expect(screen.getByLabelText("English public headline").getAttribute("required")).not.toBeNull();
  expect(screen.getByLabelText("Arabic public headline").getAttribute("dir")).toBe("rtl");
  expect((screen.getByLabelText("Person safety assessed") as HTMLInputElement).checked).toBe(false);
  expect(screen.getByRole("button", { name: "Preview public Telegram lead" })).toBeTruthy();
  expect(screen.queryByText("PRIVATE SOURCE TEXT")).toBeNull();
});

it("shows the exact public preview and requires a separate approval", async () => {
  render(await PublicationPage({ params: Promise.resolve({ id: "7" }), searchParams: Promise.resolve({ preview: hash }) }));
  expect(screen.getByText("Analyst headline")).toBeTruthy();
  expect(screen.getByText("عنوان المحلل")).toBeTruthy();
  expect(screen.getByText("Public Channel")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Approve public Telegram lead" })).toBeTruthy();
  expect((screen.getByLabelText("I personally authorize this exact public record") as HTMLInputElement).checked).toBe(false);
  expect(screen.queryByText("PRIVATE SOURCE TEXT")).toBeNull();
  expect(document.querySelector("article img")).toBeNull();
});
