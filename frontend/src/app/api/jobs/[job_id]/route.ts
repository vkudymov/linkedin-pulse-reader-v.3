import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function DELETE(
  _request: Request,
  ctx: { params: Promise<{ job_id: string }> },
) {
  const { job_id } = await ctx.params;

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  if (!job_id || typeof job_id !== "string") {
    return NextResponse.json({ ok: false, error: "invalid job id" }, { status: 400 });
  }

  const resp = await supabase.from("jobs").delete().eq("id", job_id);
  if (resp.error) {
    return NextResponse.json(
      { ok: false, error: resp.error.message || "supabase error" },
      { status: 400 },
    );
  }

  return NextResponse.json({ ok: true }, { status: 200 });
}
