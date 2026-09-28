import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PublicNewsWire, PublicTelegramWire } from "@syosint/schemas";
import { en } from "../i18n/en";
import { ReportingHub } from "./ReportingHub";

const rss: PublicNewsWire = {
  schemaVersion: "1.1.0", generatedAt: "2026-09-27T12:00:00Z", lastSuccessfulRefreshAt: "2026-09-27T12:00:00Z",
  sources: { configured: 1, healthy: 1, delayed: 0 }, sourceStates: [{ id: "rss", label: { en: "RSS source", ar: "مصدر" }, language: "en", attribution: "Source", attributionUrl: "https://example.org", status: "healthy", lastSuccessfulRefreshAt: "2026-09-27T12:00:00Z", entryCount: 1 }],
  entries: [{ id: "rss:1", sourceId: "rss", sourceLabel: { en: "RSS source", ar: "مصدر" }, language: "en", headline: "RSS report", url: "https://example.org/report", publishedAt: "2026-09-27T10:00:00Z", collectedAt: "2026-09-27T12:00:00Z" }],
};
const telegram: PublicTelegramWire = {
  schemaVersion: "1.0.0", generatedAt: "2026-09-27T13:00:00Z", lastEditorialUpdateAt: "2026-09-27T13:00:00Z",
  entries: [{ id: "telegram:42:7", status: "active", channel: { name: "Public channel", username: "publicnews", language: "mixed" }, url: "https://t.me/publicnews/7", headline: { en: "Reviewed Telegram lead", ar: "خبر راجعه محلل" }, publishedAt: "2026-09-27T11:00:00Z", approvedAt: "2026-09-27T13:00:00Z", revisions: [] }],
};

describe("ReportingHub", () => {
  it("does not describe an empty demonstration wire as a recent editorial update", () => {
    render(<ReportingHub newsWire={rss} telegramWire={{ ...telegram, entries: [] }} locale="en" dictionary={en} />);
    expect(screen.queryByText("Last editorial update")).toBeNull();
    fireEvent.click(screen.getByRole("tab", { name: "Approved Telegram" }));
    expect(screen.getByText("No approved Telegram reports are available in the past seven days.")).toBeVisible();
    expect(screen.queryByText("Last editorial update")).toBeNull();
  });
  it("merges by publication time and shares source, language and date controls across tabs", () => {
    render(<ReportingHub newsWire={rss} telegramWire={telegram} locale="en" dictionary={en} />);
    const links = screen.getAllByRole("link", { name: /report|lead/ });
    expect(links[0]).toHaveTextContent("Reviewed Telegram lead");
    expect(links[1]).toHaveTextContent("RSS report");
    fireEvent.change(screen.getByLabelText("Source filter"), { target: { value: "telegram:publicnews" } });
    expect(screen.queryByText("RSS report")).toBeNull();
    fireEvent.change(screen.getByLabelText("Language filter"), { target: { value: "ar" } });
    expect(screen.getByText("Reviewed Telegram lead")).toBeVisible();
    fireEvent.change(screen.getByLabelText("Since date"), { target: { value: "2026-09-28" } });
    expect(screen.queryByText("Reviewed Telegram lead")).toBeNull();
    fireEvent.change(screen.getByLabelText("Since date"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("tab", { name: "Approved Telegram" }));
    expect(screen.getByText("Reviewed Telegram lead")).toBeVisible();
    fireEvent.click(screen.getByRole("tab", { name: "RSS / Atom" }));
    expect(screen.queryByText("RSS report")).toBeNull();
  });
});
