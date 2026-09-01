import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";

export function getWorkerApiBaseUrl() {
  return (process.env.WORKER_API_URL || "http://127.0.0.1:8000").trim().replace(/\/+$/, "");
}

export async function getWorkerAccessToken() {
  const supabase = await createSupabaseServerClient();
  const { data: sessionData } = await supabase.auth.getSession();
  return sessionData.session?.access_token ?? null;
}

export function unauthorizedResponse() {
  return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
}

export async function forwardWorkerResponse(resp: Response) {
  const text = await resp.text();
  return new NextResponse(text, {
    status: resp.status,
    headers: { "content-type": resp.headers.get("content-type") || "application/json" },
  });
}
