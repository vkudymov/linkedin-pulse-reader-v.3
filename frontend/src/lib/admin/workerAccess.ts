import type { SupabaseClient } from "@supabase/supabase-js";

export function getWorkerApiBaseUrl() {
  return (process.env.WORKER_API_URL || "http://127.0.0.1:8000").trim().replace(/\/+$/, "");
}

/** Access token for worker API calls (RSC or route handlers). */
export async function getSupabaseAccessToken(supabase: SupabaseClient): Promise<string | null> {
  const { data: userData } = await supabase.auth.getUser();
  if (!userData.user) return null;

  const { data: refreshed, error: refreshError } = await supabase.auth.refreshSession();
  if (!refreshError && refreshed.session?.access_token) {
    return refreshed.session.access_token;
  }

  const { data: sessionData } = await supabase.auth.getSession();
  return sessionData.session?.access_token ?? null;
}
