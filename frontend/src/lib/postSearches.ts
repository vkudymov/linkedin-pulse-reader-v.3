import type { SupabaseClient } from "@supabase/supabase-js";

const SELECT =
  "id,user_id,title,status,last_run_at,created_at,updated_at,account_label,search_tariff_id,email_report_enabled,email_report_format,prompts(role,body),search_types!inner(code)";

function attachPostPrompts(row: Record<string, unknown>): Record<string, unknown> {
  const prompts = Array.isArray(row.prompts) ? (row.prompts as Array<Record<string, unknown>>) : [];
  const searchPrompt = prompts.find((p) => p && p.role === "search" && typeof p.body === "string")?.body;
  const commentPrompt = prompts.find((p) => p && p.role === "comment" && typeof p.body === "string")?.body;
  const out = {
    ...row,
    search_prompt: typeof searchPrompt === "string" ? searchPrompt : "",
    comment_prompt: typeof commentPrompt === "string" ? commentPrompt : null,
  };
  delete (out as Record<string, unknown>).prompts;
  delete (out as Record<string, unknown>).search_types;
  return out;
}

export async function loadPostSearchRows(
  supabase: SupabaseClient,
  userId: string,
): Promise<{ rows: Record<string, unknown>[]; error: { code?: string; message?: string } | null }> {
  const resp = await supabase
    .from("searches")
    .select(SELECT)
    .eq("user_id", userId)
    .eq("search_types.code", "posts")
    .order("created_at", { ascending: true });

  if (resp.error) return { rows: [], error: resp.error };
  const rows = (Array.isArray(resp.data) ? resp.data : []) as Record<string, unknown>[];
  return { rows: rows.map(attachPostPrompts), error: null };
}

