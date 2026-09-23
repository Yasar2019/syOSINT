import { execFileSync } from "node:child_process";
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
});
