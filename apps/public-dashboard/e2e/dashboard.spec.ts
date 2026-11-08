import { expect, test } from "@playwright/test";

test("switches public reporting modes and explains pending Telegram approvals in both languages", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("tab", { name: "All reporting" })).toHaveAttribute("aria-selected", "true");
  await page.getByRole("tab", { name: "Approved Telegram" }).click();
  await expect(page.getByText("No approved Telegram reports are available in the past seven days.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Live News Wire" })).toHaveCount(0);
  await page.getByRole("tab", { name: "RSS / Atom" }).click();
  await expect(page.getByRole("heading", { name: "Live News Wire" })).toBeVisible();
  await page.getByRole("button", { name: "العربية" }).click();
  await page.getByRole("tab", { name: "تيليغرام الموافق عليه" }).click();
  await expect(page.getByText("لا توجد تقارير تيليغرام موافق عليها خلال الأيام السبعة الماضية.")).toBeVisible();
  await expect(page.getByTestId("dashboard-root")).toHaveAttribute("dir", "rtl");
});

test("filters incidents and preserves filters when switching to Arabic", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Live News Wire" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Live News Wire" }).locator(".wire-disclosure")).toHaveText("Unverified external reporting");
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

test('shows a withdrawal notice without its former claim or links in both languages', async ({ page }) => {
  await page.goto('/');
  const card = page.getByTestId('incident-card').filter({ hasText: 'Synthetic report withdrawn after reassessment.' });
  await expect(card).toHaveCount(1);
  await expect(card).toContainText('Withdrawn report');
  await expect(page.getByText('[DEMO] Disputed political statement exercise', {exact:true})).toHaveCount(0);
  await card.getByRole('button').click();
  const detail = page.locator('.incident-detail');
  await expect(detail).toContainText('Synthetic report withdrawn after reassessment.');
  await expect(detail.locator('a[href*="demo-source-e"]')).toHaveCount(0);
  await expect(detail.getByText('Disputed', {exact:true})).toHaveCount(0);
  await detail.getByRole('button', {name:/close/i}).click();
  await page.getByRole('button', {name:'العربية'}).click();
  await expect(page.getByTestId('incident-card').filter({hasText:'سُحب التقرير التجريبي بعد إعادة التقييم.'})).toContainText('تقرير مسحوب');
});

test('keeps the bundled map usable without WebGL and localizes its controls', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(window, 'WebGL2RenderingContext', { value: undefined, configurable: true }));
  await page.goto('/');
  const map = page.locator('.situation-map');
  await expect(map.getByText('Detailed map unavailable. Showing the offline overview.')).toBeVisible();
  await expect(map.locator('svg')).toBeVisible();
  await expect(map.getByRole('button', { name: 'Zoom in', exact: true })).toBeDisabled();
  await expect(map.locator('.map-location-list button').first()).toBeVisible();
  await map.locator('.map-location-list button').first().click();
  await expect(page.locator('.incident-detail')).toBeVisible();
  await page.getByRole('button', {name:'العربية'}).click();
  await expect(map.getByLabel('خريطة الأساس')).toBeVisible();
  await expect(map.getByRole('button', {name:'إعادة تحميل الخريطة التفصيلية'})).toBeVisible();
});

test('renders the real vector engine, switches basemap and opens a mapped incident', async ({ page }) => {
  // Deterministic style: exercises real WebGL/worker/camera/DOM markers without relying on a tile service in CI.
  await page.route('https://tiles.openfreemap.org/styles/**', route => route.fulfill({ json: { version: 8, sources: {}, layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#101c27' } }] } }));
  await page.goto('/');
  const map = page.locator('.situation-map');
  await expect(map.locator('.detailed-map')).toHaveAttribute('data-map-status', 'ready', {timeout:20000});
  await expect(map.locator('.vector-map-host canvas')).toBeVisible();
  const marker = map.locator('.detailed-map-marker').first();
  await expect(marker).toBeVisible();
  await marker.click();
  await expect(page.locator('.incident-detail')).toBeVisible();
  await map.getByRole('button',{name:'Zoom in',exact:true}).click();
  await map.getByLabel('Basemap').selectOption('streets');
  await expect(map.locator('.detailed-map')).toHaveAttribute('data-map-status','ready');
  await expect(map.locator('.detailed-map-marker').first()).toBeVisible();
  await map.getByRole('button',{name:'Reset to Syria',exact:true}).click();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth)).toBe(false);
});
