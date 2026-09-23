import { expect, test } from "@playwright/test";

test("filters incidents and preserves filters when switching to Arabic", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("checkbox", { name: /infrastructure/i }).check();
  const countBefore = await page.locator("[data-testid='incident-card']").count();
  expect(countBefore).toBeGreaterThan(0);

  await page.getByRole("button", { name: "العربية" }).click();
  await expect(page.getByTestId("dashboard-root")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("checkbox", { name: /البنية التحتية/i })).toBeChecked();
  await expect(page.locator("[data-testid='incident-card']")).toHaveCount(countBefore);
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
