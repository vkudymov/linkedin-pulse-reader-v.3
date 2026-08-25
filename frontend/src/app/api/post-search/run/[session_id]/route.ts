import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";

function getWorkerApiBaseUrl() {
  return (process.env.WORKER_API_URL || "http://127.0.0.1:8000").trim().replace(/\/+$/, "");
}

export async function GET(_request: Request, ctx: { params: Promise<{ session_id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data: sessionData } = await supabase.auth.getSession();
  const accessToken = sessionData.session?.access_token;
  if (!accessToken) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  const { session_id } = await ctx.params;
  const baseUrl = getWorkerApiBaseUrl();
  const resp = await fetch(`${baseUrl}/v1/post-search/run/${encodeURIComponent(session_id)}`, {
    headers: { authorization: `Bearer ${accessToken}` },
  });

  const text = await resp.text();
  return new NextResponse(text, {
    status: resp.status,
    headers: { "content-type": resp.headers.get("content-type") || "application/json" },
  });
}

