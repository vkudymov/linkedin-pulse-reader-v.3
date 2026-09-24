import type { SupabaseClient } from "@supabase/supabase-js";

const SELECT =
  "id,title,search_query,location,status,last_run_at,linkedin_filters,created_at,updated_at,search_tariff_id,email_report_enabled,email_report_format,prompts(role,body),search_types!inner(code)";

function attachFilterPrompt(row: Record<string, unknown>): Record<string, unknown> {
  const prompts = Array.isArray(row.prompts) ? (row.prompts as Array<Record<string, unknown>>) : [];
  const filterPrompt = prompts.find((p) => p && p.role === "filter" && typeof p.body === "string")?.body;
  const out = { ...row, filter_prompt: typeof filterPrompt === "string" ? filterPrompt : "" };
  delete (out as Record<string, unknown>).prompts;
  delete (out as Record<string, unknown>).search_types;
  return out;
}

export async function loadJobSearchRows(
  supabase: SupabaseClient,
  userId: string,
): Promise<{
  rows: Record<string, unknown>[];
  error: { code?: string; message?: string } | null;
}> {
  const resp = await supabase
    .from("searches")
    .select(SELECT)
    .eq("user_id", userId)
    .eq("search_types.code", "jobs")
    .order("created_at", { ascending: true });

  if (resp.error) return { rows: [], error: resp.error };
  const rows = (Array.isArray(resp.data) ? resp.data : []) as Record<string, unknown>[];
  return { rows: rows.map(attachFilterPrompt), error: null };
}
