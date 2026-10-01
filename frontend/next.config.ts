import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  experimental: {
    optimizePackageImports: ['lucide-react', 'recharts'],
  },
  typescript: {
    ignoreBuildErrors: true,
  }
};

export default nextConfig;
