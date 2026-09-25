import { expect, test } from "@playwright/test";

test("filters incidents and preserves filters when switching to Arabic", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Live News Wire" })).toBeVisible();
  await expect(page.getByText("Unverified external reporting")).toBeVisible();
  await expect(page.getByText(/\d+ configured · \d+ healthy · \d+ delayed · \d+ headlines?/)).toBeVisible();
  await expect(page.getByText(/reviewed incidents are fictional demonstration data/i)).toBeVisible();
  await expect(page.getByText(/Live News Wire contains real, unverified external publisher headlines/i)).toBeVisible();
  await page.getByLabel("Language filter").selectOption("en");
  await page.getByRole("checkbox", { name: /infrastructure/i }).check();
  const countBefore = await page.locator("[data-testid='incident-card']").count();
  expect(countBefore).toBeGreaterThan(0);

  await page.getByRole("button", { name: "العربية" }).click();
  await expect(page.getByTestId("dashboard-root")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { name: "شريط الأخبار المباشر" })).toBeVisible();
  await expect(page.getByText(/\d+ مصدر مهيأ · \d+ سليم · \d+ متأخر · \d+ (?:عنوان خبري|عناوين إخبارية)/)).toBeVisible();
  await expect(page.getByText(/الحوادث المراجعة بيانات توضيحية خيالية/)).toBeVisible();
  await expect(page.getByLabel("تصفية حسب اللغة")).toHaveValue("en");
  await expect(page.getByRole("checkbox", { name: /البنية التحتية/i })).toBeChecked();
  await expect(page.locator("[data-testid='incident-card']")).toHaveCount(countBefore);
});

test("keeps wire controls usable in a narrow Arabic viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "العربية" }).click();
  await expect(page.getByLabel("تصفية حسب المصدر")).toBeVisible();
  await expect(page.getByLabel("تصفية حسب اللغة")).toBeVisible();
  await expect(page.getByText(/\d+ مصدر مهيأ · \d+ سليم · \d+ متأخر · \d+ (?:عنوان خبري|عناوين إخبارية)/)).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
});

test("paginates a populated wire without mobile overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "العربية" }).click();
  const wire = page.getByRole("region", { name: "شريط الأخبار المباشر" });

  await expect(wire.getByRole("article")).toHaveCount(25);
  await wire.getByRole("button", { name: "عرض المزيد" }).click();
  await expect(wire.getByRole("article")).toHaveCount(50);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflow).toBe(false);
});

test("supports keyboard navigation and exposes methodology", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: /skip to content/i })).toBeFocused();
  await page.getByRole("link", { name: /methodology/i }).first().click();
  await expect(page.getByRole("heading", { name: /methodology/i })).toBeVisible();
});

test("contains no runtime calls to paid or external map services", async ({ page }) => {
  const externalRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) {
      externalRequests.push(request.url());
    }
  });

  await page.goto("/");
  await expect(page.getByRole("region", { name: /syria situation map/i })).toBeVisible();
  expect(externalRequests).toEqual([]);
});
