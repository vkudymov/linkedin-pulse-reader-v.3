import { NextResponse } from "next/server";

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
    id: data.user.id,
    locale,
    updated_at: new Date().toISOString(),
  };

  const { error } = await supabase.from("user_profiles").upsert(payload);
  if (error) {
    return NextResponse.json(
      { ok: false, error: error.message || "supabase error" },
      { status: 400 },
    );
  }

  const resp = NextResponse.json({ ok: true, locale }, { status: 200 });
  resp.cookies.set("NEXT_LOCALE", locale, { path: "/" });
  return resp;
}

