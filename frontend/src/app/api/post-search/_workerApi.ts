import { NextResponse } from "next/server";

import { getSupabaseAccessToken, getWorkerApiBaseUrl } from "@/lib/admin/workerAccess";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export { getWorkerApiBaseUrl };

export async function getWorkerAccessToken() {
  const supabase = await createSupabaseServerClient();
  return getSupabaseAccessToken(supabase);
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
