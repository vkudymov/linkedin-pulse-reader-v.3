import type { SupabaseClient } from "@supabase/supabase-js";

import { LINKED_PROMPT_SELECT, attachLinkedPrompts } from "@/lib/linkedPrompts";

const SELECT =
  "id,user_id,title,status,last_run_at,created_at,updated_at,account_label,search_tariff_id,email_report_enabled,email_report_format," +
  LINKED_PROMPT_SELECT +
  ",search_types!inner(code)";

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
  const rows = (Array.isArray(resp.data) ? resp.data : []) as unknown as Record<string, unknown>[];
  return { rows: rows.map(attachLinkedPrompts), error: null };
}
