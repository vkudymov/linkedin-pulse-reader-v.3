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

  // Remove associated stored media objects first (best-effort, but fail delete if storage remove fails).
  const mediaResp = await supabase
    .from("feed_post_media")
    .select("object_path")
    .eq("feed_post_id", post_id);
  if (mediaResp.error) {
    return NextResponse.json(
      { ok: false, error: mediaResp.error.message || "supabase error" },
      { status: 400 },
    );
  }

  const objectPaths = (mediaResp.data || [])
    .map((r) => (r && typeof r === "object" ? (r as { object_path?: unknown }).object_path : null))
    .filter((p): p is string => typeof p === "string" && p.trim().length > 0);

  if (objectPaths.length > 0) {
    const { error: storageError } = await supabase.storage
      .from("post_media")
      .remove(objectPaths);
    if (storageError) {
      return NextResponse.json(
        { ok: false, error: storageError.message || "storage error" },
        { status: 400 },
      );
    }
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

