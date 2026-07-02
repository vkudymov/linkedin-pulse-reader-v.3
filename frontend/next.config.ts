import type { NextConfig } from "next";

console.log(
  `[INFO] env startup NEXT_PUBLIC_SUPABASE_URL=${process.env.NEXT_PUBLIC_SUPABASE_URL ? "ok" : "missing"} cwd=${process.cwd()}`,
);

const nextConfig = {
  turbopack: {
    root: __dirname,
  },
} as unknown as NextConfig;

export default nextConfig;
