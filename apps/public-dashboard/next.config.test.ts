import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("Next.js deployment paths", () => {
  it("uses no base path locally", async () => {
    vi.stubEnv("GITHUB_ACTIONS", "");
    const { default: config } = await import("./next.config");

    expect(config.basePath).toBe("");
    expect(config.output).toBe("export");
  });

  it("uses the repository path in GitHub Actions", async () => {
    vi.stubEnv("GITHUB_ACTIONS", "true");
    const { default: config } = await import("./next.config");

    expect(config.basePath).toBe("/syOSINT");
    expect(config.assetPrefix).toBe("/syOSINT");
  });
});
