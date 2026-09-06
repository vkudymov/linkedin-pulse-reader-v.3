import { NextResponse } from "next/server";

import { authErrorCode, parseEmailPassword } from "@/lib/auth/credentials";
import { log } from "@/lib/log/logger";
import { createSupabaseServerClient } from "@/lib/supabase/server";

function normalizeLocale(v: unknown): "ru" | "en" {
  return v === "en" ? "en" : "ru";
}

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

  const locale = normalizeLocale(
    body && typeof body === "object" && "locale" in body ? body.locale : null,
  );

  try {
    const supabase = await createSupabaseServerClient();
    const { data, error } = await supabase.auth.signUp(credentials);
    if (error) {
      const code = authErrorCode(error);
      log.error("auth.register", error.message, {
        where: "src/app/api/auth/register/route.ts",
        meta: { code: error.code },
      });
      const status = code === "network" ? 502 : 400;
      return NextResponse.json({ ok: false, error: code }, { status });
    }

    const uid = data.user?.id;
    if (uid && data.session) {
      const payload = { locale, updated_at: new Date().toISOString() };
      const { error: updateError } = await supabase
        .from("user_profiles")
        .update(payload)
        .eq("id", uid);
      if (updateError) {
        log.error("auth.register", updateError.message || "locale update failed", {
          where: "src/app/api/auth/register/route.ts",
          meta: { code: updateError.code },
        });
      }
    }

    const resp = NextResponse.json({ ok: true }, { status: 200 });
    resp.cookies.set("NEXT_LOCALE", locale, { path: "/" });
    return resp;
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "register failed";
    const code = authErrorCode(e);
    log.error("auth.register", message, { where: "src/app/api/auth/register/route.ts" });
    return NextResponse.json(
      { ok: false, error: code },
      { status: code === "network" ? 502 : 400 },
    );
  }
}
