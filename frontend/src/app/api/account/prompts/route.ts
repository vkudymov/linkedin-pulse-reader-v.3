import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";
import { validatePromptPayload } from "@/lib/validatePrompts";

type Body = { search_prompt?: unknown; comment_prompt?: unknown };

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

  const validated = validatePromptPayload(json);
  if (!validated.ok) {
    return NextResponse.json({ ok: false, error: validated.error }, { status: 400 });
  }

  const payload = {
    id: data.user.id,
    search_prompt: validated.value.search_prompt,
    comment_prompt: validated.value.comment_prompt,
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

