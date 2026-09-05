import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

console.log(
  `[INFO] env startup NEXT_PUBLIC_SUPABASE_URL=${process.env.NEXT_PUBLIC_SUPABASE_URL ? "ok" : "missing"} cwd=${process.cwd()}`,
);

const nextConfig = {
  turbopack: {
    root: __dirname,
  },
} as unknown as NextConfig;

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");
export default withNextIntl(nextConfig);
