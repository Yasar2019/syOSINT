import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PublicNewsWire } from "@syosint/schemas";
import { ar } from "../i18n/ar";
import { en } from "../i18n/en";
import { NewsWire } from "./NewsWire";

const wire: PublicNewsWire = {
  schemaVersion: "1.1.0",
  generatedAt: "2026-09-23T16:00:00Z",
  lastSuccessfulRefreshAt: "2026-09-23T15:59:00Z",
  sources: { configured: 2, healthy: 1, delayed: 1 },
  sourceStates: [
    {
      id: "bbc",
      label: { en: "BBC Arabic", ar: "بي بي سي عربي" },
      language: "ar",
      attribution: "BBC feed attribution",
      attributionUrl: "https://www.bbc.com/legal",
      status: "healthy",
      lastSuccessfulRefreshAt: "2026-09-23T15:59:00Z",
      entryCount: 1,
    },
    {
      id: "un",
      label: { en: "UN News", ar: "أخبار الأمم المتحدة" },
      language: "en",
      attribution: "UN feed attribution",
      attributionUrl: "https://www.un.org/legal",
      status: "delayed",
      lastSuccessfulRefreshAt: null,
      entryCount: 1,
    },
  ],
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
  it("summarizes retained headlines and lists configured empty and delayed sources", () => {
    const coverage: PublicNewsWire = {
      ...wire,
      lastSuccessfulRefreshAt: new Date().toISOString(),
      entries: [wire.entries[0]],
      sourceStates: [
        { ...wire.sourceStates[0], entryCount: 1 },
        { ...wire.sourceStates[1], entryCount: 0 },
      ],
    };
    render(<NewsWire wire={coverage} locale="en" dictionary={en} />);

    expect(screen.getByText("2 configured · 1 healthy · 1 delayed · 1 headline")).toBeVisible();
    expect(screen.getByRole("option", { name: /UN News.*delayed/ })).toBeVisible();
    fireEvent.change(screen.getByLabelText("Source filter"), { target: { value: "un" } });
    expect(screen.getByText("This source is delayed; recent coverage may be incomplete.")).toBeVisible();
    expect(screen.getByRole("link", { name: "UN feed attribution" })).toHaveAttribute(
      "href",
      "https://www.un.org/legal",
    );
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("explains a selected empty healthy source separately from a delayed one", () => {
    render(<NewsWire wire={{
      ...wire,
      lastSuccessfulRefreshAt: new Date().toISOString(),
      entries: [],
      sources: { configured: 2, healthy: 2, delayed: 0 },
      sourceStates: wire.sourceStates.map((source) => ({ ...source, status: "healthy", entryCount: 0 })),
    }} locale="en" dictionary={en} />);

    fireEvent.change(screen.getByLabelText("Source filter"), { target: { value: "bbc" } });
    expect(screen.getByText("No recent matching reports from this source.")).toBeVisible();
    expect(screen.getByRole("option", { name: /BBC Arabic.*no recent headlines/ })).toBeVisible();
  });

  it("does not blame another source's delay for a healthy source's language mismatch", () => {
    render(<NewsWire wire={{ ...wire, lastSuccessfulRefreshAt: new Date().toISOString() }} locale="en" dictionary={en} />);
    fireEvent.change(screen.getByLabelText("Source filter"), { target: { value: "bbc" } });
    fireEvent.change(screen.getByLabelText("Language filter"), { target: { value: "en" } });

    expect(screen.getByText("No matching news reports right now.")).toBeVisible();
    expect(screen.queryByText(/This does not mean there are no new reports/)).toBeNull();
  });

  it("explains an all-sources language mismatch without claiming the wire is empty", () => {
    render(<NewsWire wire={{
      ...wire,
      lastSuccessfulRefreshAt: new Date().toISOString(),
      entries: [wire.entries[0]],
      sourceStates: [wire.sourceStates[0], { ...wire.sourceStates[1], entryCount: 0 }],
    }} locale="en" dictionary={en} />);
    fireEvent.change(screen.getByLabelText("Language filter"), { target: { value: "en" } });

    expect(screen.getByText("No matching news reports right now.")).toBeVisible();
    expect(screen.queryByText(/No recent wire entries are available/)).toBeNull();
  });

  it("shows 25 headlines at a time and resets on source and language changes", () => {
    const many: PublicNewsWire = {
      ...wire,
      entries: Array.from({ length: 55 }, (_, index) => ({
        ...wire.entries[index % 2],
        id: `entry:${index}`,
        headline: `Headline ${index}`,
      })),
    };
    render(<NewsWire wire={many} locale="en" dictionary={en} />);

    expect(screen.getAllByRole("article")).toHaveLength(25);
    fireEvent.click(screen.getByRole("button", { name: "Show more" }));
    expect(screen.getAllByRole("article")).toHaveLength(50);
    fireEvent.change(screen.getByLabelText("Source filter"), { target: { value: "bbc" } });
    expect(screen.getAllByRole("article")).toHaveLength(25);
    fireEvent.change(screen.getByLabelText("Source filter"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Show more" }));
    fireEvent.change(screen.getByLabelText("Language filter"), { target: { value: "en" } });
    expect(screen.getAllByRole("article")).toHaveLength(25);
    expect(screen.getByRole("button", { name: "Show more" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Show more" }));
    expect(screen.getAllByRole("article")).toHaveLength(27);
    expect(screen.queryByRole("button", { name: "Show more" })).toBeNull();
  });

  it("localizes coverage and delayed source explanations in Arabic", () => {
    render(<NewsWire wire={{
      ...wire,
      entries: [],
      sourceStates: wire.sourceStates.map((source) => ({ ...source, entryCount: 0 })),
    }} locale="ar" dictionary={ar} />);

    expect(screen.getByText("2 مصدر مهيأ · 1 سليم · 1 متأخر · 0 عناوين إخبارية")).toBeVisible();
    expect(screen.getByRole("option", { name: /أخبار الأمم المتحدة.*متأخر/ })).toBeVisible();
    fireEvent.change(screen.getByLabelText("تصفية حسب المصدر"), { target: { value: "un" } });
    expect(screen.getByText("هذا المصدر متأخر؛ قد تكون التغطية الحديثة غير مكتملة.")).toBeVisible();
  });

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
    expect(screen.getAllByRole("link", { name: "BBC feed attribution" })[0]).toHaveAttribute(
      "href",
      "https://www.bbc.com/legal",
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
          sources: { configured: 2, healthy: 0, delayed: 0 },
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
          sources: { configured: 2, healthy: 0, delayed: 1 },
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
