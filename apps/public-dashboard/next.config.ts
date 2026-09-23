import type { NextConfig } from "next";

const inGitHubActions = process.env.GITHUB_ACTIONS === "true";
const basePath = inGitHubActions ? "/syOSINT" : "";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  basePath,
  assetPrefix: basePath,
  images: { unoptimized: true },
  reactStrictMode: true,
  transpilePackages: ["@syosint/schemas"],
};

export default nextConfig;
