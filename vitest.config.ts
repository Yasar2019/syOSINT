import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    projects: [
      {
        test: {
          include: ["tests/**/*.test.ts"],
          name: "repository",
        },
      },
      "packages/*/vitest.config.ts",
      "apps/*/vitest.config.ts",
    ],
  },
});
