import { log } from "@/lib/log/logger";

function stripOuterQuotes(s: string) {
  const trimmed = s.trim();
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

export function getEnv(name: string): string {
  // IMPORTANT: In Next.js client bundles, NEXT_PUBLIC_* env vars are inlined only
  // for static property access (process.env.NEXT_PUBLIC_...). Dynamic indexing
  // (process.env[name]) can be undefined in the browser.
  let value: string | undefined;
  switch (name) {
    case "NEXT_PUBLIC_SUPABASE_URL":
      value = process.env.NEXT_PUBLIC_SUPABASE_URL;
      break;
    case "NEXT_PUBLIC_SUPABASE_ANON_KEY":
      value = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
      break;
    default:
      value = process.env[name];
      break;
  }
  if (!value) {
    log.error("env.getEnv", `${name} missing`, {
      where: "src/lib/env.ts",
      hint: "Check frontend/.env.local and restart `npm run dev`.",
    });
    throw new Error(`Missing required env var: ${name}`);
  }
  return stripOuterQuotes(value);
}

