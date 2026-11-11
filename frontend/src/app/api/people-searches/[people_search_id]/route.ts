import { createSupabaseServerClient } from "@/lib/supabase/server";
import { PEOPLE_REQUIRED_MARKER } from "@/lib/defaultPrompts";
import { normalizePeopleFilters } from "@/lib/peopleFilters";
import { attachPeoplePrompt } from "@/lib/peopleSearches";
import { createOwnedPrompt, updateOwnedPromptBody } from "@/lib/promptLibrary";

function normalizeStatus(v: unknown): "active" | "paused" | null {
  if (v === "active" || v === "paused") return v;
  return null;
}

export async function PATCH(request: Request, ctx: { params: Promise<{ people_search_id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const { people_search_id } = await ctx.params;
  const exists = await supabase
    .from("searches")
    .select("id,people_prompt_id,search_types!inner(code)")
    .eq("id", people_search_id)
    .eq("user_id", data.user.id)
    .eq("search_types.code", "people")
    .maybeSingle();
  if (exists.error || !exists.data) return new Response("not found", { status: 404 });
  const currentPromptId =
    exists.data && typeof (exists.data as { people_prompt_id?: unknown }).people_prompt_id === "string"
      ? String((exists.data as { people_prompt_id: string }).people_prompt_id)
      : "";

  let json: unknown = null;
  try {
    json = await request.json();
  } catch {
    return new Response("invalid json", { status: 400 });
  }
  const body = (json && typeof json === "object" ? json : {}) as Record<string, unknown>;

  const payload: Record<string, unknown> = { updated_at: new Date().toISOString() };
  let peoplePromptToSave: string | null = null;

  if (typeof body.title === "string") payload.title = body.title.trim();
  if (typeof body.search_query === "string") payload.search_query = body.search_query.trim();
  if (typeof body.people_prompt === "string") {
    if (!body.people_prompt.includes(PEOPLE_REQUIRED_MARKER)) {
      return Response.json({ ok: false, error: `people_prompt must contain ${PEOPLE_REQUIRED_MARKER}` }, { status: 400 });
    }
    peoplePromptToSave = body.people_prompt;
  }
  if (typeof body.people_prompt_id === "string") {
    const pid = body.people_prompt_id.trim();
    if (pid) {
      const owned = await supabase
        .from("prompts")
        .select("id")
        .eq("id", pid)
        .eq("user_id", data.user.id)
        .eq("role", "people")
        .maybeSingle();
      if (owned.error || !owned.data) {
        return Response.json({ ok: false, error: "people prompt not found" }, { status: 400 });
      }
      payload.people_prompt_id = pid;
    }
  }
  const st = normalizeStatus(body.status);
  if (st) payload.status = st;
  if (body.linkedin_filters !== undefined) {
    payload.linkedin_filters = normalizePeopleFilters(body.linkedin_filters);
  }

  const updated = await supabase
    .from("searches")
    .update(payload)
    .eq("id", people_search_id)
    .eq("user_id", data.user.id)
    .select(
      "id,user_id,title,search_query,status,last_run_at,linkedin_filters,created_at,updated_at,search_tariff_id,people_prompt_id," +
        "people_prompt:prompts!searches_people_prompt_id_fkey(id,role,title,body)," +
        "search_types!inner(code)",
    )
    .maybeSingle();

  if (updated.error) return Response.json({ ok: false, error: updated.error.message }, { status: 400 });

  if (peoplePromptToSave !== null) {
    if (currentPromptId) {
      const up = await updateOwnedPromptBody(supabase, data.user.id, currentPromptId, peoplePromptToSave);
      if (up.error) return Response.json({ ok: false, error: up.error.message }, { status: 400 });
    } else {
      const createdPrompt = await createOwnedPrompt(supabase, data.user.id, "people", peoplePromptToSave);
      const pid = createdPrompt.data && typeof createdPrompt.data.id === "string" ? createdPrompt.data.id : "";
      if (createdPrompt.error || !pid) {
        return Response.json({ ok: false, error: createdPrompt.error?.message || "prompt create failed" }, { status: 400 });
      }
      await supabase
        .from("searches")
        .update({ people_prompt_id: pid })
        .eq("id", people_search_id)
        .eq("user_id", data.user.id);
    }
  }

  const row = attachPeoplePrompt((updated.data || {}) as Record<string, unknown>);
  return Response.json({ ok: true, people_search: row }, { status: 200 });
}

export async function DELETE(_request: Request, ctx: { params: Promise<{ people_search_id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const { people_search_id } = await ctx.params;
  const exists = await supabase
    .from("searches")
    .select("id,search_types!inner(code)")
    .eq("id", people_search_id)
    .eq("user_id", data.user.id)
    .eq("search_types.code", "people")
    .maybeSingle();
  if (exists.error || !exists.data) return new Response("not found", { status: 404 });
  const { error } = await supabase
    .from("searches")
    .delete()
    .eq("id", people_search_id)
    .eq("user_id", data.user.id);

  if (error) return Response.json({ ok: false, error: error.message }, { status: 400 });
  return Response.json({ ok: true }, { status: 200 });
}
