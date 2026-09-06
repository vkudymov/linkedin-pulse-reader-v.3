import { NextResponse } from "next/server";

import { authErrorCode, parseEmailPassword } from "@/lib/auth/credentials";
import { log } from "@/lib/log/logger";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function POST(request: Request) {
  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ ok: false, error: "auth_failed" }, { status: 400 });
  }

  const credentials = parseEmailPassword(body);
  if (!credentials) {
    return NextResponse.json({ ok: false, error: "invalid_credentials" }, { status: 400 });
  }

  try {
    const supabase = await createSupabaseServerClient();
    const { data, error } = await supabase.auth.signInWithPassword(credentials);
    if (error) {
      const code = authErrorCode(error);
      log.error("auth.login", error.message, {
        where: "src/app/api/auth/login/route.ts",
        meta: { code: error.code },
      });
      const status = code === "invalid_credentials" ? 401 : code === "network" ? 502 : 400;
      return NextResponse.json({ ok: false, error: code }, { status });
    }

    const uid = data.user?.id;
    if (!uid) {
      return NextResponse.json({ ok: false, error: "auth_failed" }, { status: 400 });
    }

    const { data: adminState } = await supabase
      .from("user_admin_state")
      .select("is_blocked")
      .eq("id", uid)
      .maybeSingle();
    if (adminState?.is_blocked) {
      await supabase.auth.signOut();
      return NextResponse.json({ ok: false, error: "blocked" }, { status: 403 });
    }

    const { data: pref } = await supabase
      .from("user_profiles")
      .select("locale")
      .eq("id", uid)
      .maybeSingle();
    const locale = pref?.locale === "en" ? "en" : "ru";

    const resp = NextResponse.json({ ok: true, locale }, { status: 200 });
    resp.cookies.set("NEXT_LOCALE", locale, { path: "/" });
    return resp;
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "login failed";
    const code = authErrorCode(e);
    log.error("auth.login", message, { where: "src/app/api/auth/login/route.ts" });
    return NextResponse.json(
      { ok: false, error: code },
      { status: code === "network" ? 502 : 400 },
    );
  }
}
