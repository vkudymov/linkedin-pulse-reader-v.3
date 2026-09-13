import { createSupabaseServerClient } from "@/lib/supabase/server";

const MARKER = "<<<JOB_TEXT>>>";

function normalizeStatus(v: unknown): "active" | "paused" | null {
  if (v === "active" || v === "paused") return v;
  return null;
}

function isNonEmptyString(v: unknown): v is string {
  return typeof v === "string" && v.trim().length > 0;
}

export async function GET() {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const { data: searches, error } = await supabase
    .from("job_searches")
    .select("id,title,search_query,location,filter_prompt,status,last_run_at,created_at,updated_at")
    .eq("user_id", data.user.id)
    .order("created_at", { ascending: true });

  if (error) return new Response(error.message || "load failed", { status: 400 });

  const rows = Array.isArray(searches) ? searches : [];
  const withCounts = await Promise.all(
    rows.map(async (s) => {
      const lastRunAt = typeof s.last_run_at === "string" ? s.last_run_at : null;
      if (!lastRunAt) return { ...s, new_match_count: 0 };

      const { count } = await supabase
        .from("job_analyses")
        .select("id", { count: "exact", head: true })
        .eq("job_search_id", s.id)
        .eq("match", true)
        .gte("analyzed_at", lastRunAt);

      return { ...s, new_match_count: count ?? 0 };
    }),
  );

  return Response.json({ ok: true, job_searches: withCounts });
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
  const search_query = isNonEmptyString(body.search_query) ? body.search_query.trim() : null;
  const location = typeof body.location === "string" ? body.location.trim() || null : null;
  const filter_prompt = isNonEmptyString(body.filter_prompt) ? body.filter_prompt : null;
  const status = normalizeStatus(body.status) ?? "active";

  if (!title || !search_query || !filter_prompt) {
    return Response.json({ ok: false, error: "invalid payload" }, { status: 400 });
  }
  if (!filter_prompt.includes(MARKER)) {
    return Response.json({ ok: false, error: `filter_prompt must contain ${MARKER}` }, { status: 400 });
  }

  const { data: inserted, error } = await supabase
    .from("job_searches")
    .insert({
      user_id: data.user.id,
      title,
      search_query,
      location,
      filter_prompt,
      status,
    })
    .select("id,title,search_query,location,filter_prompt,status,last_run_at,created_at,updated_at")
    .maybeSingle();

  if (error) return Response.json({ ok: false, error: error.message }, { status: 400 });
  return Response.json({ ok: true, job_search: inserted }, { status: 200 });
}

