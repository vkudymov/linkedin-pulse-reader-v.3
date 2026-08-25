import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";

function getWorkerApiBaseUrl() {
  return (process.env.WORKER_API_URL || "http://127.0.0.1:8000").trim().replace(/\/+$/, "");
}

export async function POST(request: Request) {
  const supabase = await createSupabaseServerClient();
  const { data: sessionData } = await supabase.auth.getSession();
  const accessToken = sessionData.session?.access_token;
  if (!accessToken) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  let body: unknown = null;
  try {
    body = await request.json();
  } catch {
    body = null;
  }

  const baseUrl = getWorkerApiBaseUrl();
  const resp = await fetch(`${baseUrl}/v1/post-search/run`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${accessToken}`,
      "content-type": "application/json",
    },
    body: JSON.stringify(body || {}),
  });

  const text = await resp.text();
  return new NextResponse(text, {
    status: resp.status,
    headers: { "content-type": resp.headers.get("content-type") || "application/json" },
  });
}

