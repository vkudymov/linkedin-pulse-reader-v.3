import { createBrowserClient } from "@supabase/ssr";

import { getEnv } from "@/lib/env";

export function createSupabaseBrowserClient() {
  return createBrowserClient(
    getEnv("NEXT_PUBLIC_SUPABASE_URL"),
    getEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY"),
  );
}

