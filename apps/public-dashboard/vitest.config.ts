import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["*.test.ts", "src/**/*.test.ts", "src/**/*.test.tsx"],
    name: "public-dashboard",
    setupFiles: ["./src/test/setup.ts"],
  },
});
