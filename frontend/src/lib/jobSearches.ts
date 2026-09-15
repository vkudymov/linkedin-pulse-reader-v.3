import type { SupabaseClient } from "@supabase/supabase-js";

const SELECT_WITH_FILTERS =
  "id,title,search_query,location,filter_prompt,status,last_run_at,linkedin_filters,created_at,updated_at";
const SELECT_WITHOUT_FILTERS =
  "id,title,search_query,location,filter_prompt,status,last_run_at,created_at,updated_at";

function isMissingLinkedinFiltersColumn(error: { code?: string; message?: string } | null): boolean {
  if (!error) return false;
  return error.code === "42703" || (error.message || "").includes("linkedin_filters");
}

export async function loadJobSearchRows(
  supabase: SupabaseClient,
  userId: string,
): Promise<{
  rows: Record<string, unknown>[];
  usedFiltersColumn: boolean;
  error: { code?: string; message?: string } | null;
}> {
  const first = await supabase
    .from("job_searches")
    .select(SELECT_WITH_FILTERS)
    .eq("user_id", userId)
    .order("created_at", { ascending: true });

  if (!first.error) {
    return {
      rows: Array.isArray(first.data) ? first.data : [],
      usedFiltersColumn: true,
      error: null,
    };
  }

  if (!isMissingLinkedinFiltersColumn(first.error)) {
    return { rows: [], usedFiltersColumn: false, error: first.error };
  }

  const second = await supabase
    .from("job_searches")
    .select(SELECT_WITHOUT_FILTERS)
    .eq("user_id", userId)
    .order("created_at", { ascending: true });

  return {
    rows: Array.isArray(second.data) ? second.data : [],
    usedFiltersColumn: false,
    error: second.error,
  };
}
