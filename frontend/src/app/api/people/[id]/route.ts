import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function DELETE(
  _request: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const { id } = await ctx.params;

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  if (!id || typeof id !== "string") {
    return NextResponse.json({ ok: false, error: "invalid person id" }, { status: 400 });
  }

  const resp = await supabase.from("people").delete().eq("id", id);
  if (resp.error) {
    return NextResponse.json(
      { ok: false, error: resp.error.message || "supabase error" },
      { status: 400 },
    );
  }

  return NextResponse.json({ ok: true }, { status: 200 });
}
