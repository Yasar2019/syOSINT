import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const protectedPaths = [
  ".env",
  "collector.session",
  "analysis.sqlite",
  "evidence/item.json",
  "raw-media/clip.mp4",
  "collector.log",
  ".next/cache/trace",
  "out/index.html",
  ".superpowers/tools/task-start",
];

describe("repository safety policy", () => {
  it.each(protectedPaths)("keeps %s outside version control", (path) => {
    const ignoredPath = execFileSync(
      "git",
      ["check-ignore", "--no-index", path],
      { encoding: "utf8" },
    ).trim();

    expect(ignoredPath).toBe(path);
  });

  it("keeps scheduled RSS publication inside the constrained Pages workflow", () => {
    const workflow = readFileSync(".github/workflows/rss-wire.yml", "utf8");

    expect(workflow).toMatch(/cron:\s*["']\*\/30 \* \* \* \*["']/);
    expect(workflow).toMatch(/permissions:\s*\n\s+contents:\s*read/);
    expect(workflow).toMatch(/pages:\s*write/);
    expect(workflow).toMatch(/id-token:\s*write/);
    expect(workflow).toMatch(/concurrency:\s*\n\s+group:\s*pages/);
    expect(workflow).toContain("python-version: '3.14'");
    expect(workflow).toContain("collect:rss:public");
    expect(workflow).toContain("validatePublicNewsWire");
    expect(workflow.indexOf("validatePublicNewsWire")).toBeLessThan(
      workflow.indexOf("pnpm build"),
    );
    expect(workflow).toContain("actions/upload-pages-artifact@v3");
    expect(workflow).toContain("actions/deploy-pages@v4");
  });

  it("preserves the live RSS wire during ordinary main deployments", () => {
    const workflow = readFileSync(".github/workflows/deploy-pages.yml", "utf8");

    expect(workflow).toContain("python-version: '3.14'");
    expect(workflow).toContain("collect:rss:public");
    expect(workflow).toContain(
      "https://yasar2019.github.io/syOSINT/news-wire.v1.json",
    );
    expect(workflow.indexOf("collect:rss:public")).toBeLessThan(
      workflow.indexOf("sync-public-data.mjs"),
    );
  });
});
