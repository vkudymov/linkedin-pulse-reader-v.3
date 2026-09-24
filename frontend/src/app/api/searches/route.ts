import { createSupabaseServerClient } from "@/lib/supabase/server";
import { LINKED_PROMPT_SELECT, attachLinkedPrompts } from "@/lib/linkedPrompts";
import { requireOwnedPrompt } from "@/lib/promptLibrary";
import { getSearchTypeId } from "@/lib/searchTypes";

function mapSearch(row: Record<string, unknown>) {
  const attached = attachLinkedPrompts(row);
  const st = attached.search_types;
  const code = st && typeof st === "object" && "code" in st ? String((st as { code?: unknown }).code || "") : "";
  delete attached.search_types;
  return { ...attached, search_type_code: code };
}

export async function GET(request: Request) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const url = new URL(request.url);
  const type = url.searchParams.get("type") || "";
  const status = url.searchParams.get("status") || "";
  const q = (url.searchParams.get("q") || "").trim();
  const limit = Math.max(1, Math.min(200, Number(url.searchParams.get("limit") || "50") || 50));
  const offset = Math.max(0, Number(url.searchParams.get("offset") || "0") || 0);

  let req = supabase
    .from("searches")
    .select(
      "id,user_id,title,status,last_run_at,search_tariff_id,email_report_enabled,email_report_format,search_query,location,linkedin_filters,account_label,created_at,updated_at," +
        LINKED_PROMPT_SELECT +
        ",search_types!inner(code)",
      { count: "exact" },
    )
    .eq("user_id", data.user.id);
  if (type === "jobs" || type === "posts") req = req.eq("search_types.code", type);
  if (status === "active" || status === "paused") req = req.eq("status", status);
  if (q) req = req.ilike("title", `%${q}%`);
  const resp = await req.order("created_at", { ascending: false }).range(offset, offset + limit - 1);
  if (resp.error) return Response.json({ ok: false, error: resp.error.message }, { status: 400 });
  const items = (Array.isArray(resp.data) ? resp.data : []).map((r) =>
    mapSearch(r as unknown as Record<string, unknown>),
  );
  return Response.json({ items, total: resp.count ?? items.length, limit, offset });
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
  const type = body.type === "jobs" || body.type === "posts" ? body.type : null;
  const title = typeof body.title === "string" ? body.title.trim() : "";
  if (!type || !title) return Response.json({ ok: false, error: "invalid payload" }, { status: 400 });

  const typeId = await getSearchTypeId(supabase, type);
  const payload: Record<string, unknown> = {
    user_id: data.user.id,
    search_type_id: typeId,
    title,
    status: body.status === "paused" ? "paused" : "active",
  };

  if (type === "jobs") {
    const searchQuery = typeof body.search_query === "string" ? body.search_query.trim() : "";
    const filterPromptId = typeof body.filter_prompt_id === "string" ? body.filter_prompt_id.trim() : "";
    if (!searchQuery || !filterPromptId) {
      return Response.json({ ok: false, error: "search_query and filter_prompt_id are required" }, { status: 400 });
    }
    const owned = await requireOwnedPrompt(supabase, data.user.id, filterPromptId, "filter");
    if (!owned) return Response.json({ ok: false, error: "filter prompt not found" }, { status: 400 });
    payload.search_query = searchQuery;
    payload.location = typeof body.location === "string" ? body.location.trim() || null : null;
    payload.filter_prompt_id = owned;
  } else {
    const searchPromptId = typeof body.search_prompt_id === "string" ? body.search_prompt_id.trim() : "";
    if (!searchPromptId) return Response.json({ ok: false, error: "search_prompt_id is required" }, { status: 400 });
    const owned = await requireOwnedPrompt(supabase, data.user.id, searchPromptId, "search");
    if (!owned) return Response.json({ ok: false, error: "search prompt not found" }, { status: 400 });
    payload.search_prompt_id = owned;
    const commentPromptId = typeof body.comment_prompt_id === "string" ? body.comment_prompt_id.trim() : "";
    if (commentPromptId) {
      const commentOwned = await requireOwnedPrompt(supabase, data.user.id, commentPromptId, "comment");
      if (!commentOwned) return Response.json({ ok: false, error: "comment prompt not found" }, { status: 400 });
      payload.comment_prompt_id = commentOwned;
    }
    payload.account_label = typeof body.account_label === "string" ? body.account_label.trim() || null : null;
  }

  const st = await supabase.from("user_admin_state").select("search_tariff_id").eq("id", data.user.id).maybeSingle();
  if (!st.error && st.data && typeof st.data.search_tariff_id === "string") {
    payload.search_tariff_id = st.data.search_tariff_id;
  }

  const created = await supabase
    .from("searches")
    .insert(payload)
    .select(
      "id,user_id,title,status,last_run_at,search_tariff_id,email_report_enabled,email_report_format,search_query,location,linkedin_filters,account_label,created_at,updated_at," +
        LINKED_PROMPT_SELECT +
        ",search_types!inner(code)",
    )
    .maybeSingle();
  if (created.error || !created.data) {
    return Response.json({ ok: false, error: created.error?.message || "create failed" }, { status: 400 });
  }
  return Response.json({ ok: true, search: mapSearch(created.data as unknown as Record<string, unknown>) }, { status: 200 });
}
