import { createSupabaseServerClient } from "@/lib/supabase/server";
import { normalizeLinkedInJobFilters } from "@/lib/linkedinJobFilters";

const MARKER = "<<<JOB_TEXT>>>";
const SELECT_WITH_FILTERS =
  "id,title,search_query,location,filter_prompt,status,last_run_at,linkedin_filters,created_at,updated_at";
const SELECT_WITHOUT_FILTERS =
  "id,title,search_query,location,filter_prompt,status,last_run_at,created_at,updated_at";

function normalizeStatus(v: unknown): "active" | "paused" | null {
  if (v === "active" || v === "paused") return v;
  return null;
}

function isMissingLinkedinFiltersColumn(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const e = error as { code?: unknown; message?: unknown };
  const code = typeof e.code === "string" ? e.code : "";
  const msg = typeof e.message === "string" ? e.message : "";
  return code === "42703" || msg.includes("linkedin_filters");
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
  if (body.linkedin_filters !== undefined) {
    payload.linkedin_filters = normalizeLinkedInJobFilters(body.linkedin_filters);
  }

  const first = await supabase
    .from("job_searches")
    .update(payload)
    .eq("id", job_search_id)
    .eq("user_id", data.user.id)
    .select(SELECT_WITH_FILTERS)
    .maybeSingle();

  if (!first.error) return Response.json({ ok: true, job_search: first.data }, { status: 200 });

  // Backward-compatible: if DB migration wasn't applied yet, ignore linkedin_filters.
  if (!isMissingLinkedinFiltersColumn(first.error) || payload.linkedin_filters === undefined) {
    return Response.json({ ok: false, error: first.error.message }, { status: 400 });
  }

  delete payload.linkedin_filters;
  const second = await supabase
    .from("job_searches")
    .update(payload)
    .eq("id", job_search_id)
    .eq("user_id", data.user.id)
    .select(SELECT_WITHOUT_FILTERS)
    .maybeSingle();

  if (second.error) return Response.json({ ok: false, error: second.error.message }, { status: 400 });
  return Response.json({ ok: true, job_search: second.data }, { status: 200 });
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

