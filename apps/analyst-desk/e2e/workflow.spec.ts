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
