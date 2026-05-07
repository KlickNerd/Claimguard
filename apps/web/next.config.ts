import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // ``standalone`` produces a self-contained ``.next/standalone`` build
  // that the Docker image runs as ``node server.js`` - no full
  // node_modules in the runtime image. Cuts the production image from
  // ~ 1.2 GB to ~ 300 MB.
  output: "standalone",
};

export default nextConfig;
