import { createSupabaseServerClient } from "@/lib/supabase/server";
import { normalizeLinkedInJobFilters } from "@/lib/linkedinJobFilters";
import { LINKED_PROMPT_SELECT, attachLinkedPrompts } from "@/lib/linkedPrompts";
import { createOwnedPrompt, updateOwnedPromptBody } from "@/lib/promptLibrary";

const MARKER = "<<<JOB_TEXT>>>";
const EMAIL_FORMATS = new Set(["none", "xlsx", "docx", "txt", "json", "xml"]);

function normalizeStatus(v: unknown): "active" | "paused" | null {
  if (v === "active" || v === "paused") return v;
  return null;
}

export async function PATCH(request: Request, ctx: { params: Promise<{ job_search_id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const { job_search_id } = await ctx.params;
  const exists = await supabase
    .from("searches")
    .select("id,filter_prompt_id,search_types!inner(code)")
    .eq("id", job_search_id)
    .eq("user_id", data.user.id)
    .eq("search_types.code", "jobs")
    .maybeSingle();
  if (exists.error || !exists.data) return new Response("not found", { status: 404 });
  const currentFilterId =
    exists.data && typeof (exists.data as { filter_prompt_id?: unknown }).filter_prompt_id === "string"
      ? String((exists.data as { filter_prompt_id: string }).filter_prompt_id)
      : "";

  let json: unknown = null;
  try {
    json = await request.json();
  } catch {
    return new Response("invalid json", { status: 400 });
  }
  const body = (json && typeof json === "object" ? json : {}) as Record<string, unknown>;

  const payload: Record<string, unknown> = { updated_at: new Date().toISOString() };
  let filterPromptToSave: string | null = null;

  if (typeof body.title === "string") payload.title = body.title.trim();
  if (typeof body.search_query === "string") payload.search_query = body.search_query.trim();
  if (typeof body.location === "string") payload.location = body.location.trim() || null;
  if (typeof body.filter_prompt === "string") {
    if (!body.filter_prompt.includes(MARKER)) {
      return Response.json({ ok: false, error: `filter_prompt must contain ${MARKER}` }, { status: 400 });
    }
    filterPromptToSave = body.filter_prompt;
  }
  const st = normalizeStatus(body.status);
  if (st) payload.status = st;
  if (body.linkedin_filters !== undefined) {
    payload.linkedin_filters = normalizeLinkedInJobFilters(body.linkedin_filters);
  }

  // Email report settings (gated by tariff capability).
  const wantsEmailEnabled = body.email_report_enabled === true;
  const hasEmailEnabled = body.email_report_enabled !== undefined;
  const hasEmailFormat = body.email_report_format !== undefined;
  const rawFormat = typeof body.email_report_format === "string" ? body.email_report_format.trim().toLowerCase() : null;
  const fmt = rawFormat && EMAIL_FORMATS.has(rawFormat) ? rawFormat : rawFormat ? null : null;
  if (hasEmailFormat && !fmt) {
    return Response.json({ ok: false, error: "invalid email_report_format" }, { status: 400 });
  }
  if (hasEmailEnabled) payload.email_report_enabled = Boolean(body.email_report_enabled);
  if (hasEmailFormat) payload.email_report_format = fmt ?? "none";

  if ((wantsEmailEnabled || (hasEmailFormat && fmt && fmt !== "none"))) {
    const st = await supabase
      .from("searches")
      .select("search_tariff_id,search_types!inner(code)")
      .eq("id", job_search_id)
      .eq("user_id", data.user.id)
      .eq("search_types.code", "jobs")
      .maybeSingle();
    const tariffId = !st.error && st.data && typeof st.data.search_tariff_id === "string" ? st.data.search_tariff_id : null;

    let allows = false;
    if (tariffId) {
      const t = await supabase.from("search_tariffs").select("email_reports_enabled").eq("id", tariffId).maybeSingle();
      allows = Boolean(!t.error && t.data && (t.data as { email_reports_enabled?: unknown }).email_reports_enabled === true);
    }
    if (!allows) {
      const t0 = await supabase
        .from("search_tariffs")
        .select("email_reports_enabled")
        .order("sort_order", { ascending: true })
        .order("created_at", { ascending: true })
        .limit(1)
        .maybeSingle();
      allows = Boolean(!t0.error && t0.data && (t0.data as { email_reports_enabled?: unknown }).email_reports_enabled === true);
    }
    if (!allows) {
      return Response.json({ ok: false, error: "tariff does not allow email reports" }, { status: 400 });
    }
  }

  const updated = await supabase
    .from("searches")
    .update(payload)
    .eq("id", job_search_id)
    .eq("user_id", data.user.id)
    .select(
      "id,user_id,title,search_query,location,status,last_run_at,linkedin_filters,created_at,updated_at,search_tariff_id,email_report_enabled,email_report_format," +
        LINKED_PROMPT_SELECT +
        ",search_types!inner(code)",
    )
    .maybeSingle();

  if (updated.error) return Response.json({ ok: false, error: updated.error.message }, { status: 400 });

  if (filterPromptToSave !== null) {
    if (currentFilterId) {
      const up = await updateOwnedPromptBody(supabase, data.user.id, currentFilterId, filterPromptToSave);
      if (up.error) return Response.json({ ok: false, error: up.error.message }, { status: 400 });
    } else {
      const createdPrompt = await createOwnedPrompt(supabase, data.user.id, "filter", filterPromptToSave);
      const pid = createdPrompt.data && typeof createdPrompt.data.id === "string" ? createdPrompt.data.id : "";
      if (createdPrompt.error || !pid) {
        return Response.json({ ok: false, error: createdPrompt.error?.message || "prompt create failed" }, { status: 400 });
      }
      await supabase.from("searches").update({ filter_prompt_id: pid }).eq("id", job_search_id).eq("user_id", data.user.id);
    }
  }

  const row = attachLinkedPrompts((updated.data || {}) as Record<string, unknown>);
  delete row.search_types;
  return Response.json({ ok: true, job_search: row }, { status: 200 });
}

export async function DELETE(_request: Request, ctx: { params: Promise<{ job_search_id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const { job_search_id } = await ctx.params;
  const exists = await supabase
    .from("searches")
    .select("id,search_types!inner(code)")
    .eq("id", job_search_id)
    .eq("user_id", data.user.id)
    .eq("search_types.code", "jobs")
    .maybeSingle();
  if (exists.error || !exists.data) return new Response("not found", { status: 404 });
  const { error } = await supabase
    .from("searches")
    .delete()
    .eq("id", job_search_id)
    .eq("user_id", data.user.id);

  if (error) return Response.json({ ok: false, error: error.message }, { status: 400 });
  return Response.json({ ok: true }, { status: 200 });
}

