import type { SupabaseClient } from "@supabase/supabase-js";

export async function getSearchTypeId(
  supabase: SupabaseClient,
  code: "jobs" | "posts",
): Promise<string> {
  const resp = await supabase.from("search_types").select("id").eq("code", code).maybeSingle();
  const id = !resp.error && resp.data && typeof resp.data.id === "string" ? resp.data.id : "";
  if (!id) throw new Error(`Missing search_types row for code=${code}`);
  return id;
}

