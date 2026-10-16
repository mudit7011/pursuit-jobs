import type { NextConfig } from "next";

const API = process.env.API_URL ?? "http://127.0.0.1:8765";

const nextConfig: NextConfig = {
  devIndicators: false,
  // The Python API only listens on localhost; the dashboard proxies to it so the
  // browser talks to a single origin and no CORS is needed.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
};

export default nextConfig;
