import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PublicTelegramWire } from "@syosint/schemas";
import { en } from "../i18n/en";
import { ar } from "../i18n/ar";
import { SourceReporting } from "./SourceReporting";

const telegram: PublicTelegramWire = {
  schemaVersion: "1.0.0", generatedAt: "2026-09-27T16:00:00Z", lastEditorialUpdateAt: "2026-09-27T16:00:00Z",
  entries: [{ id: "telegram:example:42", status: "corrected", channel: { name: "Example", username: "example", language: "mixed" },
    url: "https://t.me/example/42", headline: { en: "Analyst headline", ar: "عنوان المحلل" },
    publishedAt: "2026-09-27T15:00:00Z", approvedAt: "2026-09-27T16:00:00Z",
    revisions: [{ revisedAt: "2026-09-27T17:00:00Z", action: "corrected", reason: { en: "Updated detail", ar: "تحديث التفاصيل" }, previousHeadline: { en: "Earlier headline", ar: "عنوان سابق" } }],
  }],
};

describe("SourceReporting", () => {
  it("shows item-specific reviewed Telegram records and correction history", () => {
    render(<SourceReporting wire={telegram} locale="en" dictionary={en} />);
    expect(screen.getByRole("tab", { name: "All reporting" })).toBeVisible();
    fireEvent.click(screen.getByRole("tab", { name: "Approved Telegram" }));
    expect(screen.getByText("Reviewed external Telegram report — not independently verified")).toBeVisible();
    expect(screen.getByRole("link", { name: /Analyst headline/ })).toHaveAttribute("href", "https://t.me/example/42");
    expect(screen.getByText("Updated detail")).toBeVisible();
    fireEvent.change(screen.getByLabelText("Approved Telegram reports · Language filter"), { target: { value: "ar" } });
    expect(screen.getByText("Analyst headline")).toBeVisible();
  });
  it("localizes Arabic text and keeps withdrawn history without a headline link", () => {
    const withdrawn: PublicTelegramWire = { ...telegram, entries: [{ ...telegram.entries[0], status: "withdrawn", revisions: [{ revisedAt: "2026-09-27T17:00:00Z", action: "withdrawn", reason: { en: "Retracted", ar: "سُحب" } }] }] };
    render(<SourceReporting wire={withdrawn} locale="ar" dictionary={ar} />);
    fireEvent.click(screen.getByRole("tab", { name: "تيليغرام الموافق عليه" }));
    expect(screen.getByText("سُحب")).toBeVisible();
    expect(screen.queryByRole("link", { name: /عنوان المحلل/ })).toBeNull();
  });
});
