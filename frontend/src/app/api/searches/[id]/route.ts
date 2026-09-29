import { createSupabaseServerClient } from "@/lib/supabase/server";
import { LINKED_PROMPT_SELECT, attachLinkedPrompts } from "@/lib/linkedPrompts";
import { requireOwnedPrompt } from "@/lib/promptLibrary";
import { attachSearchTariff, loadSearchTariffs } from "@/lib/searchTariffs";

function mapSearch(row: Record<string, unknown>) {
  const attached = attachLinkedPrompts(row);
  const st = attached.search_types;
  const code = st && typeof st === "object" && "code" in st ? String((st as { code?: unknown }).code || "") : "";
  delete attached.search_types;
  return { ...attached, search_type_code: code };
}

export async function PATCH(request: Request, ctx: { params: Promise<{ id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });
  const { id } = await ctx.params;

  const exists = await supabase
    .from("searches")
    .select("id,search_types!inner(code)")
    .eq("id", id)
    .eq("user_id", data.user.id)
    .maybeSingle();
  if (exists.error || !exists.data) return new Response("not found", { status: 404 });
  const code =
    exists.data.search_types && typeof exists.data.search_types === "object" && "code" in exists.data.search_types
      ? String((exists.data.search_types as { code?: unknown }).code || "")
      : "";

  let json: unknown = null;
  try {
    json = await request.json();
  } catch {
    return new Response("invalid json", { status: 400 });
  }
  const body = (json && typeof json === "object" ? json : {}) as Record<string, unknown>;
  const payload: Record<string, unknown> = { updated_at: new Date().toISOString() };
  if (typeof body.title === "string") payload.title = body.title.trim();
  if (body.status === "active" || body.status === "paused") payload.status = body.status;
  if (typeof body.email_report_enabled === "boolean") payload.email_report_enabled = body.email_report_enabled;
  if (typeof body.email_report_format === "string") payload.email_report_format = body.email_report_format;

  if (code === "jobs") {
    if (typeof body.search_query === "string") payload.search_query = body.search_query.trim();
    if (typeof body.location === "string") payload.location = body.location.trim() || null;
    if (body.filter_prompt_id !== undefined) {
      const raw = typeof body.filter_prompt_id === "string" ? body.filter_prompt_id.trim() : "";
      if (!raw) return Response.json({ ok: false, error: "filter_prompt_id is required" }, { status: 400 });
      const owned = await requireOwnedPrompt(supabase, data.user.id, raw, "filter");
      if (!owned) return Response.json({ ok: false, error: "filter prompt not found" }, { status: 400 });
      payload.filter_prompt_id = owned;
    }
  } else {
    if (typeof body.account_label === "string") payload.account_label = body.account_label.trim() || null;
    if (body.search_prompt_id !== undefined) {
      const raw = typeof body.search_prompt_id === "string" ? body.search_prompt_id.trim() : "";
      if (!raw) return Response.json({ ok: false, error: "search_prompt_id is required" }, { status: 400 });
      const owned = await requireOwnedPrompt(supabase, data.user.id, raw, "search");
      if (!owned) return Response.json({ ok: false, error: "search prompt not found" }, { status: 400 });
      payload.search_prompt_id = owned;
    }
    if (body.comment_prompt_id !== undefined) {
      const raw = typeof body.comment_prompt_id === "string" ? body.comment_prompt_id.trim() : "";
      if (!raw) payload.comment_prompt_id = null;
      else {
        const owned = await requireOwnedPrompt(supabase, data.user.id, raw, "comment");
        if (!owned) return Response.json({ ok: false, error: "comment prompt not found" }, { status: 400 });
        payload.comment_prompt_id = owned;
      }
    }
  }

  const updated = await supabase
    .from("searches")
    .update(payload)
    .eq("id", id)
    .eq("user_id", data.user.id)
    .select(
      "id,user_id,title,status,last_run_at,search_tariff_id,email_report_enabled,email_report_format,search_query,location,linkedin_filters,account_label,created_at,updated_at," +
        LINKED_PROMPT_SELECT +
        ",search_types!inner(code)",
    )
    .maybeSingle();
  if (updated.error || !updated.data) {
    return Response.json({ ok: false, error: updated.error?.message || "update failed" }, { status: 400 });
  }
  const tariffs = await loadSearchTariffs(supabase);
  return Response.json(attachSearchTariff(mapSearch(updated.data as unknown as Record<string, unknown>), tariffs));
}

export async function DELETE(_request: Request, ctx: { params: Promise<{ id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });
  const { id } = await ctx.params;
  const exists = await supabase.from("searches").select("id").eq("id", id).eq("user_id", data.user.id).maybeSingle();
  if (exists.error || !exists.data) return new Response("not found", { status: 404 });
  const resp = await supabase.from("searches").delete().eq("id", id).eq("user_id", data.user.id);
  if (resp.error) return Response.json({ ok: false, error: resp.error.message }, { status: 400 });
  return Response.json({ ok: true });
}
