import { createSupabaseServerClient } from "@/lib/supabase/server";
import { attachSearchTariff, loadSearchTariffs } from "@/lib/searchTariffs";

const SEARCH_MARKER = "<<<POST_TEXT>>>";
const REQUIRED_COMMENT_MARKERS = ["<<<POST_TEXT>>>", "<<<CONTENT_TYPE>>>", "<<<MAIN_TOPICS>>>", "<<<TARGET_LANGUAGE>>>"];
const SELECT_WITH_TARIFF =
  "id,user_id,title,search_prompt,comment_prompt,account_label,status,last_run_at,created_at,updated_at,search_tariff_id,email_report_enabled,email_report_format";
const SELECT_WITHOUT_TARIFF =
  "id,user_id,title,search_prompt,comment_prompt,account_label,status,last_run_at,created_at,updated_at,email_report_enabled,email_report_format";

function isMissingTariffColumn(error: unknown): boolean {
  if (!error || typeof error !== "object") return false;
  const e = error as { code?: unknown; message?: unknown };
  const code = typeof e.code === "string" ? e.code : "";
  const msg = typeof e.message === "string" ? e.message : "";
  return (
    code === "42703" ||
    msg.includes("search_tariff_id") ||
    msg.includes("email_report_enabled") ||
    msg.includes("email_report_format")
  );
}

function isNonEmptyString(v: unknown): v is string {
  return typeof v === "string" && v.trim().length > 0;
}

function missingMarkers(value: string, markers: string[]): string[] {
  return markers.filter((m) => !value.includes(m));
}

export async function GET() {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const first = await supabase
    .from("post_searches")
    .select(SELECT_WITH_TARIFF)
    .eq("user_id", data.user.id)
    .order("created_at", { ascending: true });

  const tariffs = await loadSearchTariffs(supabase);

  if (!first.error) {
    const rows = (Array.isArray(first.data) ? first.data : []).map((s) =>
      attachSearchTariff((s || {}) as Record<string, unknown>, tariffs),
    );
    return Response.json({ ok: true, post_searches: rows });
  }
  if (!isMissingTariffColumn(first.error)) {
    return Response.json({ ok: false, error: first.error.message }, { status: 400 });
  }
  const second = await supabase
    .from("post_searches")
    .select(SELECT_WITHOUT_TARIFF)
    .eq("user_id", data.user.id)
    .order("created_at", { ascending: true });
  if (second.error) return Response.json({ ok: false, error: second.error.message }, { status: 400 });
  const rows = (Array.isArray(second.data) ? second.data : []).map((s) =>
    attachSearchTariff((s || {}) as Record<string, unknown>, tariffs),
  );
  return Response.json({ ok: true, post_searches: rows });
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
  const search_prompt = isNonEmptyString(body.search_prompt) ? body.search_prompt.trim() : null;
  const rawComment = typeof body.comment_prompt === "string" ? body.comment_prompt.trim() : "";
  const comment_prompt = rawComment || null;
  const account_label = typeof body.account_label === "string" ? body.account_label.trim() || null : null;
  const status = typeof body.status === "string" ? body.status.trim() || "active" : "active";

  if (!title || !search_prompt) return Response.json({ ok: false, error: "invalid payload" }, { status: 400 });
  if (!search_prompt.includes(SEARCH_MARKER)) {
    return Response.json({ ok: false, error: `search_prompt must contain ${SEARCH_MARKER}` }, { status: 400 });
  }
  if (comment_prompt) {
    const missing = missingMarkers(comment_prompt, REQUIRED_COMMENT_MARKERS);
    if (missing.length > 0) {
      return Response.json({ ok: false, error: `comment_prompt must contain markers: ${missing.join(", ")}` }, { status: 400 });
    }
  }

  const st = await supabase
    .from("user_admin_state")
    .select("search_tariff_id")
    .eq("id", data.user.id)
    .maybeSingle();
  const userTariffId =
    !st.error && st.data && typeof st.data.search_tariff_id === "string" ? st.data.search_tariff_id : null;

  const first = await supabase
    .from("post_searches")
    .insert({
      user_id: data.user.id,
      title,
      search_prompt,
      comment_prompt,
      account_label,
      status,
      search_tariff_id: userTariffId,
    })
    .select(SELECT_WITH_TARIFF)
    .maybeSingle();

  if (!first.error) return Response.json({ ok: true, post_search: first.data }, { status: 200 });
  if (!isMissingTariffColumn(first.error)) {
    return Response.json({ ok: false, error: first.error.message }, { status: 400 });
  }

  const second = await supabase
    .from("post_searches")
    .insert({
      user_id: data.user.id,
      title,
      search_prompt,
      comment_prompt,
      account_label,
      status,
    })
    .select(SELECT_WITHOUT_TARIFF)
    .maybeSingle();

  if (second.error) return Response.json({ ok: false, error: second.error.message }, { status: 400 });
  return Response.json({ ok: true, post_search: second.data }, { status: 200 });
}

