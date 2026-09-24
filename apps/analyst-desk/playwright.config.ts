import { defineConfig, devices } from "@playwright/test";

const suffix = process.pid;
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  use: { baseURL: "http://127.0.0.1:3001", ...devices["Desktop Chrome"] },
  webServer: [
    {
      command: "python e2e/api_harness.py",
      url: "http://127.0.0.1:8765/openapi.json",
      reuseExistingServer: false,
      env: {
        PYTHONPATH: "../../services/collector-api",
        SYOSINT_DB_PATH: `/tmp/syosint-browser-${suffix}.sqlite3`,
        SYOSINT_EXPORT_DIR: `/tmp/syosint-browser-export-${suffix}`,
        SYOSINT_RSS_SCHEDULER: "0",
      },
    },
    { command: "pnpm start", url: "http://127.0.0.1:3001", reuseExistingServer: false },
  ],
});
