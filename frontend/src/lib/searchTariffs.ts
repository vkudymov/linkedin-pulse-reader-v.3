import type { SupabaseClient } from "@supabase/supabase-js";

export type SearchTariffInfo = {
  id: string;
  title: string;
  max_scan_count: number;
  target_found_count: number;
  min_relevance_percent: number;
};

export function isSearchTariffInfo(v: unknown): v is SearchTariffInfo {
  if (!v || typeof v !== "object") return false;
  const r = v as Record<string, unknown>;
  return (
    typeof r.id === "string" &&
    typeof r.title === "string" &&
    typeof r.max_scan_count === "number" &&
    typeof r.target_found_count === "number" &&
    typeof r.min_relevance_percent === "number"
  );
}

export function pickSearchTariff(
  tariffId: string | null | undefined,
  tariffs: SearchTariffInfo[],
): SearchTariffInfo | null {
  if (tariffId) {
    const found = tariffs.find((row) => row.id === tariffId);
    if (found) return found;
  }
  return tariffs[0] ?? null;
}

export async function loadSearchTariffs(supabase: SupabaseClient): Promise<SearchTariffInfo[]> {
  const resp = await supabase
    .from("search_tariffs")
    .select("id,title,max_scan_count,target_found_count,min_relevance_percent")
    .order("sort_order", { ascending: true })
    .order("created_at", { ascending: true });
  return Array.isArray(resp.data) ? resp.data.filter(isSearchTariffInfo) : [];
}

export function attachSearchTariff<T extends Record<string, unknown>>(
  row: T,
  tariffs: SearchTariffInfo[],
): T & { search_tariff: SearchTariffInfo | null; target_found_count: number } {
  const tid = typeof row.search_tariff_id === "string" ? row.search_tariff_id : null;
  const tariff = pickSearchTariff(tid, tariffs);
  return {
    ...row,
    search_tariff: tariff,
    target_found_count: tariff?.target_found_count ?? 10,
  };
}
