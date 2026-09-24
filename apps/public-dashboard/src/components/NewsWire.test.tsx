import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PublicNewsWire } from "@syosint/schemas";
import { ar } from "../i18n/ar";
import { en } from "../i18n/en";
import { NewsWire } from "./NewsWire";

const wire: PublicNewsWire = {
  schemaVersion: "1.0.0",
  generatedAt: "2026-09-23T16:00:00Z",
  lastSuccessfulRefreshAt: "2026-09-23T15:59:00Z",
  sources: { healthy: 1, delayed: 1 },
  entries: [
    {
      id: "bbc:1",
      sourceId: "bbc",
      sourceLabel: { en: "BBC Arabic", ar: "بي بي سي عربي" },
      language: "ar",
      headline: "خبر تجريبي عن سوريا",
      url: "https://example.org/ar",
      publishedAt: "2026-09-23T15:55:00Z",
      collectedAt: "2026-09-23T16:00:00Z",
    },
    {
      id: "un:1",
      sourceId: "un",
      sourceLabel: { en: "UN News", ar: "أخبار الأمم المتحدة" },
      language: "en",
      headline: "Syria test report",
      url: "https://example.org/en",
      publishedAt: "2026-09-23T15:45:00Z",
      collectedAt: "2026-09-23T16:00:00Z",
    },
  ],
};

describe("NewsWire", () => {
  it("keeps the unverified disclosure and safe original-language links visible", () => {
    render(<NewsWire wire={wire} locale="en" dictionary={en} />);

    expect(screen.getByRole("heading", { name: "Live News Wire" })).toBeVisible();
    expect(screen.getByText("Unverified external reporting")).toBeVisible();
    expect(screen.getByText(/1 source delayed/)).toBeVisible();
    expect(screen.getByText(/Last successful refresh/)).toBeVisible();
    expect(screen.getByRole("link", { name: /خبر تجريبي/ })).toHaveAttribute(
      "rel",
      "noopener noreferrer",
    );

    fireEvent.change(screen.getByLabelText("Source filter"), {
      target: { value: "bbc" },
    });
    expect(screen.queryByText("Syria test report")).toBeNull();
    expect(screen.getByText("خبر تجريبي عن سوريا")).toBeVisible();

    fireEvent.change(screen.getByLabelText("Source filter"), {
      target: { value: "" },
    });

    fireEvent.change(screen.getByLabelText("Language filter"), {
      target: { value: "en" },
    });
    expect(screen.queryByText("خبر تجريبي عن سوريا")).toBeNull();
    expect(screen.getByText("Syria test report")).toBeVisible();
  });

  it("renders Arabic labels and the empty state", () => {
    render(
      <NewsWire
        wire={{
          ...wire,
          lastSuccessfulRefreshAt: new Date().toISOString(),
          entries: [],
          sources: { healthy: 0, delayed: 0 },
        }}
        locale="ar"
        dictionary={ar}
      />,
    );

    expect(screen.getByRole("heading", { name: "شريط الأخبار المباشر" })).toBeVisible();
    expect(screen.getByText("تقارير خارجية غير متحقق منها")).toBeVisible();
    expect(screen.getByText("لا توجد أخبار مطابقة حالياً.")).toBeVisible();
  });

  it("warns when the last successful refresh is stale", async () => {
    render(
      <NewsWire
        wire={{
          ...wire,
          lastSuccessfulRefreshAt: "2020-01-01T00:00:00Z",
          entries: [],
          sources: { healthy: 0, delayed: 1 },
        }}
        locale="en"
        dictionary={en}
      />,
    );

    await waitFor(() =>
      expect(
        screen.getByText("The wire refresh is delayed; headlines may be incomplete."),
      ).toBeVisible(),
    );
    expect(screen.getByText(/This does not mean there are no new reports/)).toBeVisible();
  });
});
