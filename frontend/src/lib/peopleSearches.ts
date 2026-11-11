import type { SupabaseClient } from "@supabase/supabase-js";

const SELECT =
  "id,title,search_query,status,last_run_at,linkedin_filters,created_at,updated_at,search_tariff_id," +
  "people_prompt_id," +
  "people_prompt:prompts!searches_people_prompt_id_fkey(id,role,title,body)," +
  "search_types!inner(code)";

function promptBody(value: unknown): string {
  if (value && typeof value === "object" && typeof (value as { body?: unknown }).body === "string") {
    return String((value as { body: string }).body || "");
  }
  return "";
}

export function attachPeoplePrompt(row: Record<string, unknown>): Record<string, unknown> {
  const out = { ...row };
  out.people_prompt = promptBody(row.people_prompt);
  delete out.search_types;
  return out;
}

export async function loadPeopleSearchRows(
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
    .eq("search_types.code", "people")
    .order("created_at", { ascending: true });

  if (resp.error) return { rows: [], error: resp.error };
  const rows = (Array.isArray(resp.data) ? resp.data : []) as unknown as Record<string, unknown>[];
  return { rows: rows.map(attachPeoplePrompt), error: null };
}
