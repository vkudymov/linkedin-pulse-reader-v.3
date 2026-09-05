import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { log } from "@/lib/log/logger";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("NEXT_LOCALE")?.value;
  const locale = localeCookie === "en" ? "en" : "ru";

  try {
    const supabase = await createSupabaseServerClient();
    const { error } = await supabase.auth.signOut();
    if (error) {
      log.error("auth.logout", "signOut failed", {
        where: "src/app/logout/route.ts",
        meta: { code: error.code },
      });
    }
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "logout error";
    log.error("auth.logout", message, { where: "src/app/logout/route.ts" });
    throw e;
  }
  return NextResponse.redirect(new URL(`/${locale}/login`, request.url));
}

