import { defineConfig } from "vitest/config";

export default defineConfig({
  esbuild: {
    jsx: "automatic",
  },
  test: {
    environment: "jsdom",
    include: ["*.test.ts", "scripts/**/*.test.ts", "src/**/*.test.ts", "src/**/*.test.tsx"],
    name: "public-dashboard",
    setupFiles: ["./src/test/setup.ts"],
  },
});
