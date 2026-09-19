import { createSupabaseServerClient } from "@/lib/supabase/server";

const SEARCH_MARKER = "<<<POST_TEXT>>>";
const REQUIRED_COMMENT_MARKERS = ["<<<POST_TEXT>>>", "<<<CONTENT_TYPE>>>", "<<<MAIN_TOPICS>>>", "<<<TARGET_LANGUAGE>>>"];

function missingMarkers(value: string, markers: string[]): string[] {
  return markers.filter((m) => !value.includes(m));
}

export async function PATCH(request: Request, ctx: { params: Promise<{ post_search_id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const { post_search_id } = await ctx.params;

  let json: unknown = null;
  try {
    json = await request.json();
  } catch {
    return new Response("invalid json", { status: 400 });
  }
  const body = (json && typeof json === "object" ? json : {}) as Record<string, unknown>;

  const payload: Record<string, unknown> = { updated_at: new Date().toISOString() };
  if (typeof body.title === "string") payload.title = body.title.trim();
  if (typeof body.status === "string") payload.status = body.status.trim();
  if (typeof body.account_label === "string") payload.account_label = body.account_label.trim() || null;
  if (typeof body.search_prompt === "string") {
    const sp = body.search_prompt.trim();
    if (!sp.includes(SEARCH_MARKER)) {
      return Response.json({ ok: false, error: `search_prompt must contain ${SEARCH_MARKER}` }, { status: 400 });
    }
    payload.search_prompt = sp;
  }
  if (body.comment_prompt !== undefined) {
    const raw = typeof body.comment_prompt === "string" ? body.comment_prompt.trim() : "";
    const cp = raw || null;
    if (cp) {
      const missing = missingMarkers(cp, REQUIRED_COMMENT_MARKERS);
      if (missing.length > 0) {
        return Response.json({ ok: false, error: `comment_prompt must contain markers: ${missing.join(", ")}` }, { status: 400 });
      }
    }
    payload.comment_prompt = cp;
  }

  const resp = await supabase
    .from("post_searches")
    .update(payload)
    .eq("id", post_search_id)
    .eq("user_id", data.user.id)
    .select("id,user_id,title,search_prompt,comment_prompt,account_label,status,last_run_at,created_at,updated_at")
    .maybeSingle();

  if (resp.error) return Response.json({ ok: false, error: resp.error.message }, { status: 400 });
  return Response.json({ ok: true, post_search: resp.data }, { status: 200 });
}

export async function DELETE(_request: Request, ctx: { params: Promise<{ post_search_id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const { post_search_id } = await ctx.params;
  const resp = await supabase.from("post_searches").delete().eq("id", post_search_id).eq("user_id", data.user.id);
  if (resp.error) return Response.json({ ok: false, error: resp.error.message }, { status: 400 });
  return Response.json({ ok: true }, { status: 200 });
}

