import { createSupabaseServerClient } from "@/lib/supabase/server";
import { loadJobSearchRows } from "@/lib/jobSearches";
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

function isNonEmptyString(v: unknown): v is string {
  return typeof v === "string" && v.trim().length > 0;
}

function isMissingLinkedinFiltersColumn(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const e = error as { code?: unknown; message?: unknown };
  const code = typeof e.code === "string" ? e.code : "";
  const msg = typeof e.message === "string" ? e.message : "";
  return code === "42703" || msg.includes("linkedin_filters");
}

export async function GET() {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const loaded = await loadJobSearchRows(supabase, data.user.id);
  if (loaded.error) return new Response(loaded.error.message || "load failed", { status: 400 });

  const rows = loaded.rows;
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
  const linkedin_filters = normalizeLinkedInJobFilters(body.linkedin_filters);

  if (!title || !search_query || !filter_prompt) {
    return Response.json({ ok: false, error: "invalid payload" }, { status: 400 });
  }
  if (!filter_prompt.includes(MARKER)) {
    return Response.json({ ok: false, error: `filter_prompt must contain ${MARKER}` }, { status: 400 });
  }

  const first = await supabase
    .from("job_searches")
    .insert({
      user_id: data.user.id,
      title,
      search_query,
      location,
      filter_prompt,
      status,
      linkedin_filters,
    })
    .select(SELECT_WITH_FILTERS)
    .maybeSingle();

  if (!first.error) return Response.json({ ok: true, job_search: first.data }, { status: 200 });

  // Backward-compatible: if DB migration wasn't applied yet, ignore linkedin_filters.
  if (!isMissingLinkedinFiltersColumn(first.error)) {
    return Response.json({ ok: false, error: first.error.message }, { status: 400 });
  }

  const second = await supabase
    .from("job_searches")
    .insert({
      user_id: data.user.id,
      title,
      search_query,
      location,
      filter_prompt,
      status,
    })
    .select(SELECT_WITHOUT_FILTERS)
    .maybeSingle();

  if (second.error) return Response.json({ ok: false, error: second.error.message }, { status: 400 });
  return Response.json({ ok: true, job_search: second.data }, { status: 200 });
}

