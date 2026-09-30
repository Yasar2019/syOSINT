import { expect, test } from "@playwright/test";

test("collect and promote a synthetic RSS item through the private inbox", async ({ page }) => {
  const submit = async (name: string) => {
    const completed = page.waitForResponse((response) => response.request().method() === "POST" && response.url().startsWith("http://127.0.0.1:3001/"));
    await page.getByRole("button", { name }).click();
    await completed;
    await page.waitForLoadState("networkidle");
  };

  await page.goto("/rss");
  await page.getByLabel("Display name").fill("Synthetic RSS source");
  await page.getByLabel("Public homepage URL").fill("https://feed.example");
  await page.getByLabel("RSS or Atom URL").fill("https://feed.example/rss.xml");
  await submit("Add private feed");
  await expect(page.getByText("Synthetic RSS source")).toBeVisible();

  await submit("Collect now");
  await expect(page.getByRole("link", { name: "Synthetic Syria feed report" })).toBeVisible();
  await page.getByLabel("Analyst English title").fill("Analyst-reviewed Syria report");
  await page.getByLabel("العنوان الذي كتبه المحلل").fill("تقرير سوريا راجعه المحلل");
  await submit("Promote after review");

  const caseLink = page.getByRole("link", { name: /#\d+/ });
  await expect(caseLink).toBeVisible();
  const incidentId = Number((await caseLink.getAttribute("href"))?.split("/").pop());
  const incident = await (await page.request.get(`http://127.0.0.1:8765/incidents/${incidentId}`)).json() as { state: string };
  const evidence = await (await page.request.get(`http://127.0.0.1:8765/incidents/${incidentId}/evidence`)).json() as unknown[];
  expect(incident.state).toBe("triage");
  expect(evidence).toHaveLength(1);
});

test("review and export a synthetic case through the private desk", async ({ page }) => {
  const submit = async (name: string) => {
    const completed = page.waitForResponse((response) => response.request().method() === "POST" && response.url().startsWith("http://127.0.0.1:3001/"));
    await page.getByRole("button", { name }).click();
    await completed;
    await page.waitForLoadState("networkidle");
  };
  await page.goto("/");
  await page.getByLabel("Display name").fill("Synthetic journal");
  await page.getByLabel("Public HTTPS URL").fill("https://example.org");
  await submit("Add public source");
  await expect(page.getByText("Synthetic journal").first()).toBeVisible();

  await page.getByLabel("English title").fill("Synthetic outage");
  await page.getByLabel("العنوان بالعربية").fill("انقطاع تجريبي");
  await submit("Create incident");
  await expect(page).toHaveURL(/\/incident\/\d+/);
  const caseId = Number(page.url().match(/\/incident\/(\d+)/)?.[1]);
  const readCase = async () => (await (await page.request.get(`http://127.0.0.1:8765/incidents/${caseId}`)).json()) as { state: string; summary_en?: string; review?: { human_approved?: boolean } };
  await page.getByLabel("Registered public source").selectOption({ label: "Synthetic journal" });
  await page.getByLabel("Exact public report URL").fill("https://example.org/report");
  await page.getByLabel("Original text (private only)").fill("LOCAL PRIVATE REPORT");
  await submit("Attach evidence");
  await expect(page.getByText("LOCAL PRIVATE REPORT")).toBeVisible();

  await page.getByLabel("Original summary · English").fill("An outage was reported.");
  await page.getByLabel("الملخص · عربي").fill("ورد تقرير عن انقطاع.");
  await page.getByLabel("Unknowns / contradictions · English").fill("Cause unknown.");
  await page.getByLabel("الشكوك · عربي").fill("السبب غير معروف.");
  await page.getByLabel("Safe public location label · English").fill("Syria");
  await page.getByLabel("الموقع العام · عربي").fill("سوريا");
  await page.getByLabel("Event time · ISO UTC").fill("2026-09-23T10:00:00Z");
  await submit("Save public fields");
  await expect.poll(async () => (await readCase()).summary_en).toBe("An outage was reported.");
  await page.reload();
  await expect(page.getByLabel("Original summary · English")).toHaveValue("An outage was reported.");
  await page.getByLabel("Reason for transition").fill("Initial triage completed");
  await submit("Move to investigating");
  await expect.poll(async () => (await readCase()).state).toBe("investigating");
  await expect(page.getByRole("button", { name: "Move to review-ready" })).toBeVisible();
  await page.getByLabel("Reason for transition").fill("Evidence assessed locally");
  await submit("Move to review-ready");
  await expect.poll(async () => (await readCase()).state).toBe("review-ready");
  await expect(page.getByRole("button", { name: "Move to approved" })).toBeVisible();

  await page.getByLabel("Written rationale").fill("One original reference; claim remains unverified.");
  for (const label of ["Source independence assessed", "Time consistency assessed", "Location consistency assessed", "Contradictions assessed", "No ordinary-person identification or exposed civilians", "No active tactical positions, routes, shelters or medical sites", "Remaining uncertainty and contradictions acknowledged", "I personally reviewed this case for publication"]) {
    await page.getByLabel(label).check();
  }
  await submit("Record review");
  await expect.poll(async () => (await readCase()).review?.human_approved).toBe(true);
  await page.reload();
  await expect(page.getByLabel("I personally reviewed this case for publication")).toBeChecked();
  await page.getByLabel("Reason for transition").fill("Publication check complete");
  await submit("Move to approved");
  await expect.poll(async () => (await readCase()).state).toBe("approved");

  const preview = page.locator(".preview pre");
  await expect(preview).toContainText("An outage was reported.");
  await expect(preview).not.toContainText("LOCAL PRIVATE REPORT");
  await page.getByLabel("I checked this exact public record and authorize a local export").check();
  await submit("Export sanitized JSON locally");
  await expect(page.getByRole("status")).toContainText("Sanitized JSON saved locally");
});

test("unified queue filters local RSS reports and requires analyst promotion", async ({ page }) => {
  const submit = async (button: string) => {
    const completed = page.waitForResponse((response) => response.request().method() === "POST" && response.url().startsWith("http://127.0.0.1:3001/"));
    await page.getByRole("button", { name: button }).click();
    await completed;
    await page.waitForLoadState("networkidle");
  };
  await page.goto("/telegram");
  await expect(page.getByText("Authenticated locally")).toBeVisible();
  await page.goto("/rss");
  await page.getByLabel("Display name").fill("Unified queue fixture");
  await page.getByLabel("Public homepage URL").fill("https://unified.example");
  await page.getByLabel("RSS or Atom URL").fill("https://unified.example/rss.xml");
  await submit("Add private feed");
  const fixture = page.getByRole("listitem").filter({ hasText: "Unified queue fixture" });
  await fixture.getByRole("button", { name: "Collect now" }).click();
  await page.waitForLoadState("networkidle");
  await page.goto("/intake");
  await page.getByLabel("Platform").selectOption("rss");
  await page.getByLabel("Status").selectOption("new");
  await page.getByLabel("Source").selectOption({ label: "Unified queue fixture" });
  await page.getByRole("button", { name: "Apply filters" }).click();
  const item = page.locator("article.feed-item");
  await expect(item).toHaveCount(1);
  await expect(item).toContainText("Synthetic Syria feed report");
  await expect(item).toContainText("Stored locally — never public automatically");
  await item.getByLabel("Analyst English title").fill("Reviewed unified report");
  await item.getByLabel("العنوان الذي كتبه المحلل").fill("تقرير موحد راجعه المحلل");
  const promoted = page.waitForResponse((response) => response.request().method() === "POST" && response.url().startsWith("http://127.0.0.1:3001/"));
  await item.getByRole("button", { name: "Promote after review" }).click();
  await promoted;
  await page.waitForLoadState("networkidle");
  await page.goto("/intake?platform=rss&status=promoted");
  const cases = await (await page.request.get("http://127.0.0.1:8765/incidents")).json() as Array<{ id: number; title_en: string; state: string }>;
  const incident = cases.find((entry) => entry.title_en === "Reviewed unified report");
  expect(incident?.state).toBe("triage");
  const evidence = await (await page.request.get(`http://127.0.0.1:8765/incidents/${incident?.id}/evidence`)).json() as unknown[];
  expect(evidence).toHaveLength(1);
  await expect(page.getByText("Synthetic Syria feed report").first()).toBeVisible();
});

test("approve a synthetic public channel and keep collected posts private", async ({ page }) => {
  const submit = async (name: string) => {
    const completed = page.waitForResponse((response) => response.request().method() === "POST" && response.url().startsWith("http://127.0.0.1:3001/"));
    await page.getByRole("button", { name }).click();
    await completed;
    await page.waitForLoadState("networkidle");
  };
  await page.goto("/telegram");
  await page.getByLabel("Public channel username").fill("publicnews");
  await submit("Preview channel");
  await expect(page.getByText("Synthetic Public News", { exact: true })).toBeVisible();
  await submit("Approve channel for local collection");
  await expect(page.getByText("Synthetic Public News")).toBeVisible();
  await submit("Sync channel now");
  await expect(page.getByText("<img src=x onerror=alert(1)> Synthetic local post")).toBeVisible();
  expect(await page.locator("article img").count()).toBe(0);
  const items = await (await page.request.get("http://127.0.0.1:8765/intake-items?status=new")).json() as Array<{ platform: string; text: string }>;
  expect(items.some((item) => item.platform === "telegram" && item.text.includes("Synthetic local post"))).toBe(true);
  await page.goto("/intake?platform=telegram&status=new");
  await expect(page.getByText("<img src=x onerror=alert(1)> Synthetic local post")).toBeVisible();
  await expect(page.getByText("Stored locally — never public automatically")).toBeVisible();
});

test("review, correct, and withdraw an individual Telegram lead locally", async ({ page }) => {
  const endpoint = "http://127.0.0.1:8765";
  const channels = await (await page.request.get(`${endpoint}/telegram/channels`)).json() as Array<{ id: number }>;
  const sourceId = channels[0]?.id ?? (await (await page.request.post(`${endpoint}/telegram/channels`, {
    data: { username: "publicnews", channel_id: 42, title: "Synthetic Public News", language: "ar" },
  })).json() as { id: number }).id;
  await page.request.post(`${endpoint}/telegram/channels/${sourceId}/sync`);
  const items = await (await page.request.get(`${endpoint}/intake-items?status=new`)).json() as Array<{ id: number; platform: string }>;
  const post = items.find((item) => item.platform === "telegram");
  expect(post).toBeDefined();
  const itemId = post!.id;
  const submit = async (name: string) => {
    const completed = page.waitForResponse((response) => response.request().method() === "POST" && response.url().startsWith("http://127.0.0.1:3001/"));
    await page.getByRole("button", { name }).click();
    await completed;
    await page.waitForLoadState("networkidle");
  };

  await page.goto(`/telegram/publication/${itemId}`);
  await expect(page.getByText("Original Telegram text stays private")).toBeVisible();
  await page.getByLabel("English public headline").fill("Analyst-reviewed synthetic lead");
  await page.getByLabel("Arabic public headline").fill("خبر تجريبي راجعه المحلل");
  for (const label of ["Public channel identity and original link checked", "Person safety assessed", "Operational safety assessed", "I personally reviewed this source for publication"]) {
    await page.getByLabel(label).check();
  }
  await submit("Preview public Telegram lead");
  await expect(page.getByLabel("Exact sanitized public record")).toContainText("Analyst-reviewed synthetic lead");
  await expect(page.getByLabel("Exact sanitized public record")).not.toContainText("Synthetic local post");
  await page.getByLabel("I personally authorize this exact public record").check();
  await submit("Approve public Telegram lead");
  await expect(page.getByRole("status")).toContainText("saved locally");
  const approved = await (await page.request.get(`${endpoint}/intake-items/${itemId}/publication`)).json() as { id: number; status: string };
  expect(approved.status).toBe("active");

  await page.getByLabel("Corrected English headline").fill("Corrected analyst headline");
  await page.getByLabel("English correction reason").fill("Attribution clarification");
  await page.getByLabel("Arabic correction reason").fill("توضيح النسبة");
  for (const label of ["Public channel identity and original link checked", "Person safety assessed", "Operational safety assessed", "I approve this correction"]) {
    await page.getByLabel(label).check();
  }
  await submit("Save explicit correction");
  await expect(page.getByText("Reviewed lead · corrected")).toBeVisible();

  await page.getByLabel("English withdrawal reason").fill("Source withdrew the claim");
  await page.getByLabel("Arabic withdrawal reason").fill("سحب المصدر الادعاء");
  await page.getByLabel("I authorize the public withdrawal marker").check();
  await submit("Save explicit withdrawal");
  await expect(page.getByText("Reviewed lead · withdrawn")).toBeVisible();
  expect((await (await page.request.get(`${endpoint}/intake-items/${itemId}/publication`)).json() as { status: string }).status).toBe("withdrawn");
});

test("candidate review preserves rejection history and never activates sources", async ({ page }) => {
  const endpoint = "http://127.0.0.1:8765";
  const sourcesBefore = await (await page.request.get(`${endpoint}/sources`)).json() as unknown[];
  const channelsBefore = await (await page.request.get(`${endpoint}/telegram/channels`)).json() as unknown[];
  const submit = async (scope: ReturnType<typeof page.locator>, name: string) => {
    const completed = page.waitForResponse((response) => response.request().method() === "POST" && response.url().startsWith("http://127.0.0.1:3001/"));
    await scope.getByRole("button", { name, exact: true }).click();
    await completed;
    await page.waitForLoadState("networkidle");
  };
  for (const [platform, url, name] of [
    ["web", "https://candidate.example/research", "Synthetic web candidate"],
    ["telegram", "https://t.me/candidate_news", "Synthetic channel candidate"],
  ]) {
    await page.goto("/candidates");
    await expect(page.getByText("It does not start collection", { exact: false })).toBeVisible();
    await page.locator("form").filter({ has: page.getByRole("button", { name: "Submit candidate", exact: true }) }).locator('select[name="platform"]').selectOption(platform);
    await page.getByLabel("Public HTTPS URL").fill(url);
    await page.getByLabel("Display name").fill(name);
    await page.getByLabel("Suggestion reason").fill("Synthetic source for manual policy review");
    await submit(page.locator("main"), "Submit candidate");
    let candidate = page.locator("article.feed-item").filter({ hasText: name });
    await expect(candidate).toContainText("No reviews yet.");
    await candidate.getByLabel("Review reason").fill("Provenance requires further review");
    await submit(candidate, "Record review");
    await page.getByRole("navigation", { name: "Candidate status" }).getByRole("link", { name: "Rejected", exact: true }).click();
    candidate = page.locator("article.feed-item").filter({ hasText: name });
    await expect(candidate).toContainText("Provenance requires further review");
    await page.reload();
    await expect(candidate).toContainText("Public accessibility: unchecked");
    await candidate.locator('select[name="decision"]').selectOption("accepted");
    await candidate.getByLabel("Review reason").fill("All five source policy checks completed by analyst");
    for (const label of ["Public accessibility", "Syria relevance", "Publisher/channel identity and impersonation", "Provenance", "Collection/reuse policy"]) {
      await candidate.getByLabel(label, { exact: true }).check();
    }
    await submit(candidate, "Record review");
    await page.getByRole("navigation", { name: "Candidate status" }).getByRole("link", { name: "Accepted", exact: true }).click();
    candidate = page.locator("article.feed-item").filter({ hasText: name });
    await page.reload();
    await expect(candidate).toContainText("Provenance requires further review");
    await expect(candidate).toContainText("All five source policy checks completed by analyst");
    await expect(candidate.locator("ol > li")).toHaveCount(2);
    await expect(candidate.locator("ol > li").first()).toContainText("rejected");
    await expect(candidate.locator("ol > li").last()).toContainText("accepted");
  }
  expect(await (await page.request.get(`${endpoint}/sources`)).json()).toEqual(sourcesBefore);
  expect(await (await page.request.get(`${endpoint}/telegram/channels`)).json()).toEqual(channelsBefore);
});
