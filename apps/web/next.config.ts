import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // ``standalone`` produces a self-contained ``.next/standalone`` build
  // that the Docker image runs as ``node server.js`` - no full
  // node_modules in the runtime image. Cuts the production image from
  // ~ 1.2 GB to ~ 300 MB.
  output: "standalone",
  // In a pnpm monorepo Next's file tracer otherwise stops at ``apps/web``
  // and misses the workspace-level ``node_modules`` where pnpm hoists the
  // real ``next`` package. Pointing tracing at the repo root pulls in the
  // full hoisted tree so the standalone bundle resolves modules at runtime.
  outputFileTracingRoot: path.join(__dirname, "../../"),
};

export default nextConfig;
