import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { log } from "@/lib/log/logger";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("NEXT_LOCALE")?.value;
  const locale = localeCookie === "en" ? "en" : "ru";
  const nextRaw = url.searchParams.get("next") || `/${locale}/posts`;
  const next = nextRaw.startsWith("/ru/") || nextRaw.startsWith("/en/") ? nextRaw : `/${locale}${nextRaw.startsWith("/") ? "" : "/"}${nextRaw}`;

  if (code) {
    try {
      const supabase = await createSupabaseServerClient();
      const { error } = await supabase.auth.exchangeCodeForSession(code);
      if (error) {
        log.error("auth.callback", "exchangeCodeForSession failed", {
          where: "src/app/auth/callback/route.ts",
          meta: { code: error.code },
        });
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "callback error";
      log.error("auth.callback", message, { where: "src/app/auth/callback/route.ts" });
      throw e;
    }
  } else {
    log.warn("auth.callback", "missing code", { where: "src/app/auth/callback/route.ts" });
  }

  return NextResponse.redirect(new URL(next, request.url));
}

