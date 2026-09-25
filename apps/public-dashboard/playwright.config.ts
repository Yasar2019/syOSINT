import { defineConfig, devices } from "@playwright/test";
import { randomUUID } from "node:crypto";

const fixtureSessionId = process.env.SYOSINT_E2E_SESSION_ID ?? randomUUID();
process.env.SYOSINT_E2E_SESSION_ID = fixtureSessionId;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"], ["html", { open: "never" }]],
  globalTeardown: "./scripts/e2e-global-teardown.mjs",
  use: {
    baseURL: "http://127.0.0.1:4173",
    reducedMotion: "reduce",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command:
      "node scripts/e2e-fixture-server.mjs",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: false,
    timeout: 120_000,
    env: { SYOSINT_E2E_SESSION_ID: fixtureSessionId },
  },
});
