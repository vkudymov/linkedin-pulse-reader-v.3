import { createSupabaseServerClient } from "@/lib/supabase/server";

const SEARCH_MARKER = "<<<POST_TEXT>>>";
const REQUIRED_COMMENT_MARKERS = ["<<<POST_TEXT>>>", "<<<CONTENT_TYPE>>>", "<<<MAIN_TOPICS>>>", "<<<TARGET_LANGUAGE>>>"];
const EMAIL_FORMATS = new Set(["none", "xlsx", "docx", "txt", "json", "xml"]);

function missingMarkers(value: string, markers: string[]): string[] {
  return markers.filter((m) => !value.includes(m));
}

export async function PATCH(request: Request, ctx: { params: Promise<{ post_search_id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const { post_search_id } = await ctx.params;
  const exists = await supabase
    .from("searches")
    .select("id,search_types!inner(code)")
    .eq("id", post_search_id)
    .eq("user_id", data.user.id)
    .eq("search_types.code", "posts")
    .maybeSingle();
  if (exists.error || !exists.data) return new Response("not found", { status: 404 });

  let json: unknown = null;
  try {
    json = await request.json();
  } catch {
    return new Response("invalid json", { status: 400 });
  }
  const body = (json && typeof json === "object" ? json : {}) as Record<string, unknown>;

  const payload: Record<string, unknown> = { updated_at: new Date().toISOString() };
  let searchPromptToSave: string | null = null;
  let commentPromptToSave: string | null = null;
  if (typeof body.title === "string") payload.title = body.title.trim();
  if (typeof body.status === "string") payload.status = body.status.trim();
  if (typeof body.account_label === "string") payload.account_label = body.account_label.trim() || null;
  if (typeof body.search_prompt === "string") {
    const sp = body.search_prompt.trim();
    if (!sp.includes(SEARCH_MARKER)) {
      return Response.json({ ok: false, error: `search_prompt must contain ${SEARCH_MARKER}` }, { status: 400 });
    }
    searchPromptToSave = sp;
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
    commentPromptToSave = cp;
  }

  // Email report settings (gated by tariff capability).
  const wantsEmailEnabled = body.email_report_enabled === true;
  const hasEmailEnabled = body.email_report_enabled !== undefined;
  const hasEmailFormat = body.email_report_format !== undefined;
  const rawFormat = typeof body.email_report_format === "string" ? body.email_report_format.trim().toLowerCase() : null;
  const fmt = rawFormat && EMAIL_FORMATS.has(rawFormat) ? rawFormat : rawFormat ? null : null;
  if (hasEmailFormat && !fmt) {
    return Response.json(
      { ok: false, error: "invalid email_report_format" },
      { status: 400 },
    );
  }
  if (hasEmailEnabled) payload.email_report_enabled = Boolean(body.email_report_enabled);
  if (hasEmailFormat) payload.email_report_format = fmt ?? "none";

  if ((wantsEmailEnabled || (hasEmailFormat && fmt && fmt !== "none"))) {
    // Resolve tariff for this search to enforce capability.
    const st = await supabase
      .from("searches")
      .select("search_tariff_id,search_types!inner(code)")
      .eq("id", post_search_id)
      .eq("user_id", data.user.id)
      .eq("search_types.code", "posts")
      .maybeSingle();
    const tariffId = !st.error && st.data && typeof st.data.search_tariff_id === "string" ? st.data.search_tariff_id : null;

    let allows = false;
    if (tariffId) {
      const t = await supabase.from("search_tariffs").select("email_reports_enabled").eq("id", tariffId).maybeSingle();
      allows = Boolean(!t.error && t.data && (t.data as { email_reports_enabled?: unknown }).email_reports_enabled === true);
    }
    if (!allows) {
      // fallback to default tariff
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

  const resp = await supabase
    .from("searches")
    .update(payload)
    .eq("id", post_search_id)
    .eq("user_id", data.user.id)
    .select(
      "id,user_id,title,account_label,status,last_run_at,created_at,updated_at,search_tariff_id,email_report_enabled,email_report_format,prompts(role,body),search_types!inner(code)",
    )
    .maybeSingle();

  if (resp.error) return Response.json({ ok: false, error: resp.error.message }, { status: 400 });

  if (searchPromptToSave !== null) {
    const up = await supabase
      .from("prompts")
      .upsert({ search_id: post_search_id, role: "search", body: searchPromptToSave }, { onConflict: "search_id,role" });
    if (up.error) return Response.json({ ok: false, error: up.error.message }, { status: 400 });
  }
  if (commentPromptToSave !== null) {
    if (commentPromptToSave) {
      const up = await supabase
        .from("prompts")
        .upsert({ search_id: post_search_id, role: "comment", body: commentPromptToSave }, { onConflict: "search_id,role" });
      if (up.error) return Response.json({ ok: false, error: up.error.message }, { status: 400 });
    } else {
      const del = await supabase.from("prompts").delete().eq("search_id", post_search_id).eq("role", "comment");
      if (del.error) return Response.json({ ok: false, error: del.error.message }, { status: 400 });
    }
  }

  const row = (resp.data || {}) as Record<string, unknown>;
  const prompts = Array.isArray((row as { prompts?: unknown }).prompts)
    ? ((row as { prompts: Array<Record<string, unknown>> }).prompts || [])
    : [];
  const search_prompt = prompts.find((p) => p.role === "search" && typeof p.body === "string")?.body;
  const comment_prompt = prompts.find((p) => p.role === "comment" && typeof p.body === "string")?.body ?? null;
  delete (row as Record<string, unknown>).prompts;
  delete (row as Record<string, unknown>).search_types;
  return Response.json(
    {
      ok: true,
      post_search: {
        ...row,
        search_prompt: typeof search_prompt === "string" ? search_prompt : "",
        comment_prompt: typeof comment_prompt === "string" ? comment_prompt : null,
      },
    },
    { status: 200 },
  );
}

export async function DELETE(_request: Request, ctx: { params: Promise<{ post_search_id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const { post_search_id } = await ctx.params;
  const exists = await supabase
    .from("searches")
    .select("id,search_types!inner(code)")
    .eq("id", post_search_id)
    .eq("user_id", data.user.id)
    .eq("search_types.code", "posts")
    .maybeSingle();
  if (exists.error || !exists.data) return new Response("not found", { status: 404 });
  const resp = await supabase.from("searches").delete().eq("id", post_search_id).eq("user_id", data.user.id);
  if (resp.error) return Response.json({ ok: false, error: resp.error.message }, { status: 400 });
  return Response.json({ ok: true }, { status: 200 });
}

