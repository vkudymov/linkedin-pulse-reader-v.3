import { createSupabaseServerClient } from "@/lib/supabase/server";

const SEARCH_MARKER = "<<<POST_TEXT>>>";
const REQUIRED_COMMENT_MARKERS = ["<<<POST_TEXT>>>", "<<<CONTENT_TYPE>>>", "<<<MAIN_TOPICS>>>", "<<<TARGET_LANGUAGE>>>"];

function isNonEmptyString(v: unknown): v is string {
  return typeof v === "string" && v.trim().length > 0;
}

function missingMarkers(value: string, markers: string[]): string[] {
  return markers.filter((m) => !value.includes(m));
}

export async function GET() {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const resp = await supabase
    .from("post_searches")
    .select("id,user_id,title,search_prompt,comment_prompt,account_label,status,last_run_at,created_at,updated_at")
    .eq("user_id", data.user.id)
    .order("created_at", { ascending: true });

  if (resp.error) return Response.json({ ok: false, error: resp.error.message }, { status: 400 });
  return Response.json({ ok: true, post_searches: resp.data || [] });
}

export async function POST(request: Request) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  let json: unknown = null;
  try {
    json = await request.json();
  } catch {
    return new Response("invalid json", { status: 400 });
  }
  const body = (json && typeof json === "object" ? json : {}) as Record<string, unknown>;

  const title = isNonEmptyString(body.title) ? body.title.trim() : null;
  const search_prompt = isNonEmptyString(body.search_prompt) ? body.search_prompt.trim() : null;
  const rawComment = typeof body.comment_prompt === "string" ? body.comment_prompt.trim() : "";
  const comment_prompt = rawComment || null;
  const account_label = typeof body.account_label === "string" ? body.account_label.trim() || null : null;
  const status = typeof body.status === "string" ? body.status.trim() || "active" : "active";

  if (!title || !search_prompt) return Response.json({ ok: false, error: "invalid payload" }, { status: 400 });
  if (!search_prompt.includes(SEARCH_MARKER)) {
    return Response.json({ ok: false, error: `search_prompt must contain ${SEARCH_MARKER}` }, { status: 400 });
  }
  if (comment_prompt) {
    const missing = missingMarkers(comment_prompt, REQUIRED_COMMENT_MARKERS);
    if (missing.length > 0) {
      return Response.json({ ok: false, error: `comment_prompt must contain markers: ${missing.join(", ")}` }, { status: 400 });
    }
  }

  const resp = await supabase
    .from("post_searches")
    .insert({
      user_id: data.user.id,
      title,
      search_prompt,
      comment_prompt,
      account_label,
      status,
    })
    .select("id,user_id,title,search_prompt,comment_prompt,account_label,status,last_run_at,created_at,updated_at")
    .maybeSingle();

  if (resp.error) return Response.json({ ok: false, error: resp.error.message }, { status: 400 });
  return Response.json({ ok: true, post_search: resp.data }, { status: 200 });
}

