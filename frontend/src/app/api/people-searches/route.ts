import { createSupabaseServerClient } from "@/lib/supabase/server";
import { PEOPLE_REQUIRED_MARKER } from "@/lib/defaultPrompts";
import { normalizePeopleFilters } from "@/lib/peopleFilters";
import { loadPeopleSearchRows } from "@/lib/peopleSearches";
import { createOwnedPrompt } from "@/lib/promptLibrary";
import { attachSearchTariff, loadSearchTariffs } from "@/lib/searchTariffs";
import { getSearchTypeId } from "@/lib/searchTypes";

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

  const loaded = await loadPeopleSearchRows(supabase, data.user.id);
  if (loaded.error) return new Response(loaded.error.message || "load failed", { status: 400 });

  const tariffs = await loadSearchTariffs(supabase);
  const { rows } = loaded;
  const withCounts = await Promise.all(
    rows.map(async (s) => {
      const lastRunAt = typeof s.last_run_at === "string" ? s.last_run_at : null;
      const withTariff = attachSearchTariff(s, tariffs);
      if (!lastRunAt) {
        return { ...withTariff, new_match_count: 0 };
      }

      const { count } = await supabase
        .from("people_analyses")
        .select("id", { count: "exact", head: true })
        .eq("search_id", s.id)
        .eq("match", true)
        .gte("analyzed_at", lastRunAt);

      return { ...withTariff, new_match_count: count ?? 0 };
    }),
  );

  return Response.json({ ok: true, people_searches: withCounts });
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
  const people_prompt = isNonEmptyString(body.people_prompt) ? body.people_prompt : null;
  const people_prompt_id = isNonEmptyString(body.people_prompt_id) ? body.people_prompt_id.trim() : null;
  const status = normalizeStatus(body.status) ?? "active";
  const linkedin_filters = normalizePeopleFilters(body.linkedin_filters);

  if (!title || !search_query) {
    return Response.json({ ok: false, error: "invalid payload" }, { status: 400 });
  }
  if (people_prompt && !people_prompt.includes(PEOPLE_REQUIRED_MARKER)) {
    return Response.json({ ok: false, error: `people_prompt must contain ${PEOPLE_REQUIRED_MARKER}` }, { status: 400 });
  }
  if (!people_prompt && !people_prompt_id) {
    return Response.json({ ok: false, error: "people prompt is required" }, { status: 400 });
  }

  const st = await supabase
    .from("user_admin_state")
    .select("search_tariff_id")
    .eq("id", data.user.id)
    .maybeSingle();
  const userTariffId =
    !st.error && st.data && typeof st.data.search_tariff_id === "string" ? st.data.search_tariff_id : null;

  const typeId = await getSearchTypeId(supabase, "people");
  const created = await supabase
    .from("searches")
    .insert({
      user_id: data.user.id,
      search_type_id: typeId,
      title,
      search_query,
      status,
      linkedin_filters,
      search_tariff_id: userTariffId,
    })
    .select(
      "id,user_id,title,search_query,status,last_run_at,linkedin_filters,created_at,updated_at,search_tariff_id",
    )
    .maybeSingle();

  if (created.error) return Response.json({ ok: false, error: created.error.message }, { status: 400 });
  const search = created.data as Record<string, unknown>;

  let promptId = people_prompt_id || "";
  let promptBody = people_prompt || "";
  if (people_prompt_id) {
    const owned = await supabase
      .from("prompts")
      .select("id,body")
      .eq("id", people_prompt_id)
      .eq("user_id", data.user.id)
      .eq("role", "people")
      .maybeSingle();
    if (owned.error || !owned.data) {
      await supabase.from("searches").delete().eq("id", search.id).eq("user_id", data.user.id);
      return Response.json({ ok: false, error: "people prompt not found" }, { status: 400 });
    }
    promptId = owned.data.id as string;
    promptBody = typeof owned.data.body === "string" ? owned.data.body : "";
  } else if (people_prompt) {
    const promptResp = await createOwnedPrompt(supabase, data.user.id, "people", people_prompt, title);
    promptId = promptResp.data && typeof promptResp.data.id === "string" ? promptResp.data.id : "";
    if (promptResp.error || !promptId) {
      await supabase.from("searches").delete().eq("id", search.id).eq("user_id", data.user.id);
      return Response.json({ ok: false, error: promptResp.error?.message || "prompt create failed" }, { status: 400 });
    }
  }

  const link = await supabase
    .from("searches")
    .update({ people_prompt_id: promptId })
    .eq("id", search.id)
    .eq("user_id", data.user.id);
  if (link.error) {
    await supabase.from("searches").delete().eq("id", search.id).eq("user_id", data.user.id);
    return Response.json({ ok: false, error: link.error.message }, { status: 400 });
  }

  return Response.json(
    { ok: true, people_search: { ...search, people_prompt_id: promptId, people_prompt: promptBody } },
    { status: 200 },
  );
}
