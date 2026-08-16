import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Hide the floating dev-tools indicator (bottom-left "N") in `next dev`.
  devIndicators: false,
};

export default nextConfig;
