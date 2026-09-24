import { createSupabaseServerClient } from "@/lib/supabase/server";
import { loadPostSearchRows } from "@/lib/postSearches";
import { createOwnedPrompt } from "@/lib/promptLibrary";
import { attachSearchTariff, loadSearchTariffs } from "@/lib/searchTariffs";
import { getSearchTypeId } from "@/lib/searchTypes";

const SEARCH_MARKER = "<<<POST_TEXT>>>";
const REQUIRED_COMMENT_MARKERS = ["<<<POST_TEXT>>>", "<<<CONTENT_TYPE>>>", "<<<MAIN_TOPICS>>>", "<<<TARGET_LANGUAGE>>>"];

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

  const tariffs = await loadSearchTariffs(supabase);
  const loaded = await loadPostSearchRows(supabase, data.user.id);
  if (loaded.error) return Response.json({ ok: false, error: loaded.error.message }, { status: 400 });
  const rows = loaded.rows.map((s) => attachSearchTariff((s || {}) as Record<string, unknown>, tariffs));
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

  const typeId = await getSearchTypeId(supabase, "posts");
  const created = await supabase
    .from("searches")
    .insert({
      user_id: data.user.id,
      search_type_id: typeId,
      title,
      account_label,
      status,
      search_tariff_id: userTariffId,
    })
    .select("id,user_id,title,account_label,status,last_run_at,created_at,updated_at,search_tariff_id,email_report_enabled,email_report_format")
    .maybeSingle();

  if (created.error) return Response.json({ ok: false, error: created.error.message }, { status: 400 });
  const search = created.data as Record<string, unknown>;

  const searchPromptResp = await createOwnedPrompt(supabase, data.user.id, "search", search_prompt, title);
  const searchPromptId =
    searchPromptResp.data && typeof searchPromptResp.data.id === "string" ? searchPromptResp.data.id : "";
  if (searchPromptResp.error || !searchPromptId) {
    await supabase.from("searches").delete().eq("id", search.id).eq("user_id", data.user.id);
    return Response.json({ ok: false, error: searchPromptResp.error?.message || "prompt create failed" }, { status: 400 });
  }
  let commentPromptId: string | null = null;
  if (comment_prompt) {
    const commentPromptResp = await createOwnedPrompt(supabase, data.user.id, "comment", comment_prompt, title);
    commentPromptId =
      commentPromptResp.data && typeof commentPromptResp.data.id === "string" ? commentPromptResp.data.id : null;
    if (commentPromptResp.error || !commentPromptId) {
      await supabase.from("searches").delete().eq("id", search.id).eq("user_id", data.user.id);
      return Response.json({ ok: false, error: commentPromptResp.error?.message || "prompt create failed" }, { status: 400 });
    }
  }
  const link = await supabase
    .from("searches")
    .update({ search_prompt_id: searchPromptId, comment_prompt_id: commentPromptId })
    .eq("id", search.id)
    .eq("user_id", data.user.id);
  if (link.error) {
    await supabase.from("searches").delete().eq("id", search.id).eq("user_id", data.user.id);
    return Response.json({ ok: false, error: link.error.message }, { status: 400 });
  }

  return Response.json(
    {
      ok: true,
      post_search: {
        ...search,
        search_prompt_id: searchPromptId,
        comment_prompt_id: commentPromptId,
        search_prompt,
        comment_prompt,
        account_label,
      },
    },
    { status: 200 },
  );
}

