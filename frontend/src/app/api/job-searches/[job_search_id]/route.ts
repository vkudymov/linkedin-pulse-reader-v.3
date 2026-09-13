import { createSupabaseServerClient } from "@/lib/supabase/server";

const MARKER = "<<<JOB_TEXT>>>";

function normalizeStatus(v: unknown): "active" | "paused" | null {
  if (v === "active" || v === "paused") return v;
  return null;
}

export async function PATCH(request: Request, ctx: { params: Promise<{ job_search_id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const { job_search_id } = await ctx.params;

  let json: unknown = null;
  try {
    json = await request.json();
  } catch {
    return new Response("invalid json", { status: 400 });
  }
  const body = (json && typeof json === "object" ? json : {}) as Record<string, unknown>;

  const payload: Record<string, unknown> = { updated_at: new Date().toISOString() };

  if (typeof body.title === "string") payload.title = body.title.trim();
  if (typeof body.search_query === "string") payload.search_query = body.search_query.trim();
  if (typeof body.location === "string") payload.location = body.location.trim() || null;
  if (typeof body.filter_prompt === "string") {
    if (!body.filter_prompt.includes(MARKER)) {
      return Response.json({ ok: false, error: `filter_prompt must contain ${MARKER}` }, { status: 400 });
    }
    payload.filter_prompt = body.filter_prompt;
  }
  const st = normalizeStatus(body.status);
  if (st) payload.status = st;

  const { data: updated, error } = await supabase
    .from("job_searches")
    .update(payload)
    .eq("id", job_search_id)
    .eq("user_id", data.user.id)
    .select("id,title,search_query,location,filter_prompt,status,last_run_at,created_at,updated_at")
    .maybeSingle();

  if (error) return Response.json({ ok: false, error: error.message }, { status: 400 });
  return Response.json({ ok: true, job_search: updated }, { status: 200 });
}

export async function DELETE(_request: Request, ctx: { params: Promise<{ job_search_id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const { job_search_id } = await ctx.params;
  const { error } = await supabase
    .from("job_searches")
    .delete()
    .eq("id", job_search_id)
    .eq("user_id", data.user.id);

  if (error) return Response.json({ ok: false, error: error.message }, { status: 400 });
  return Response.json({ ok: true }, { status: 200 });
}

