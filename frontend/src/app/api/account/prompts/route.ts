import { NextResponse } from "next/server";

import { COMMENT_REQUIRED_MARKERS, SEARCH_REQUIRED_MARKER } from "@/lib/defaultPrompts";
import { createSupabaseServerClient } from "@/lib/supabase/server";

type Body = {
  search_prompt?: unknown;
  comment_prompt?: unknown;
};

function missingMarkers(value: string, markers: readonly string[]) {
  const v = value || "";
  return markers.filter((m) => !v.includes(m));
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

  const rawSearch = typeof json.search_prompt === "string" ? json.search_prompt : "";
  const rawComment = typeof json.comment_prompt === "string" ? json.comment_prompt : "";

  const search_prompt = rawSearch.trim();
  const comment_prompt_trimmed = rawComment.trim();
  const comment_prompt = comment_prompt_trimmed || null;

  if (!search_prompt) {
    return NextResponse.json({ ok: false, error: "Промпт поиска обязателен." }, { status: 400 });
  }
  if (!search_prompt.includes(SEARCH_REQUIRED_MARKER)) {
    return NextResponse.json(
      { ok: false, error: `Промпт поиска должен содержать маркер ${SEARCH_REQUIRED_MARKER}.` },
      { status: 400 }
    );
  }
  if (comment_prompt) {
    const missing = missingMarkers(comment_prompt, [...COMMENT_REQUIRED_MARKERS]);
    if (missing.length > 0) {
      return NextResponse.json(
        { ok: false, error: `Промпт комментария должен содержать маркеры: ${missing.join(", ")}.` },
        { status: 400 }
      );
    }
  }

  const payload = {
    id: data.user.id,
    search_prompt,
    comment_prompt,
    updated_at: new Date().toISOString(),
  };

  const { error } = await supabase.from("user_prompts").upsert(payload);
  if (error) {
    return NextResponse.json(
      { ok: false, error: error.message || "supabase error" },
      { status: 400 }
    );
  }

  return NextResponse.json({ ok: true }, { status: 200 });
}

