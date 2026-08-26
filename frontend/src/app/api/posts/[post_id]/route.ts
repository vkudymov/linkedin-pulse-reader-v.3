import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function DELETE(
  _request: Request,
  ctx: { params: Promise<{ post_id: string }> },
) {
  const { post_id } = await ctx.params;

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  if (!post_id || typeof post_id !== "string") {
    return NextResponse.json({ ok: false, error: "invalid post id" }, { status: 400 });
  }

  const resp = await supabase.from("feed_posts").delete().eq("id", post_id);
  if (resp.error) {
    return NextResponse.json(
      { ok: false, error: resp.error.message || "supabase error" },
      { status: 400 },
    );
  }

  return NextResponse.json({ ok: true }, { status: 200 });
}

