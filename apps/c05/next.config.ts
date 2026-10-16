import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Standalone output emits a self-contained server plus only the node_modules
  // actually imported. A Cloud Run image can then omit dev dependencies and the
  // build toolchain, which shrinks the image and keeps build tooling out of
  // production.
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
