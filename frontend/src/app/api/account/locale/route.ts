import { NextResponse } from "next/server";

import { log } from "@/lib/log/logger";
import { createSupabaseServerClient } from "@/lib/supabase/server";

type Body = {
  locale?: unknown;
};

function normalizeLocale(v: unknown): "ru" | "en" | null {
  if (typeof v !== "string") return null;
  const s = v.trim().toLowerCase();
  if (s === "ru" || s === "en") return s;
  return null;
}

export async function POST(request: Request) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  let json: Body = {};
  try {
    json = (await request.json()) as Body;
  } catch {
    return NextResponse.json({ ok: false, error: "invalid json" }, { status: 400 });
  }

  const locale = normalizeLocale(json.locale);
  if (!locale) {
    return NextResponse.json({ ok: false, error: "invalid locale" }, { status: 400 });
  }

  const payload = {
    locale,
    updated_at: new Date().toISOString(),
  };

  const { data: updated, error } = await supabase
    .from("user_profiles")
    .update(payload)
    .eq("id", data.user.id)
    .select("id")
    .maybeSingle();

  if (error) {
    log.error("account.locale", error.message || "supabase error", {
      where: "src/app/api/account/locale/route.ts",
      meta: { code: error.code },
    });
    const missingColumn =
      error.code === "PGRST204" ||
      /could not find the 'locale' column/i.test(error.message || "");
    if (!missingColumn) {
      return NextResponse.json(
        { ok: false, error: error.message || "supabase error" },
        { status: 400 },
      );
    }
  } else if (!updated) {
    const { error: insertError } = await supabase.from("user_profiles").insert({
      id: data.user.id,
      ...payload,
    });
    if (insertError) {
      log.error("account.locale", insertError.message || "insert failed", {
        where: "src/app/api/account/locale/route.ts",
        meta: { code: insertError.code },
      });
      return NextResponse.json(
        { ok: false, error: insertError.message || "supabase error" },
        { status: 400 },
      );
    }
  }

  const resp = NextResponse.json({ ok: true, locale }, { status: 200 });
  resp.cookies.set("NEXT_LOCALE", locale, { path: "/" });
  return resp;
}

