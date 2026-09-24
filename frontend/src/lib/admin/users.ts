import type { SupabaseClient } from "@supabase/supabase-js";

import { getSupabaseAccessToken, getWorkerApiBaseUrl } from "@/lib/admin/workerAccess";

export type AdminUserOption = {
  id: string;
  email: string | null;
  full_name: string | null;
};

export type AdminUserRow = AdminUserOption & {
  created_at: string | null;
  is_admin: boolean;
  is_blocked: boolean;
  blocked_at: string | null;
  post_search_run_count: number;
};

export async function loadAdminUsers(accessToken: string): Promise<AdminUserRow[]> {
  const resp = await fetch(`${getWorkerApiBaseUrl()}/v1/admin/users`, {
    method: "GET",
    cache: "no-store",
    headers: { authorization: `Bearer ${accessToken}` },
  });
  const parsed: unknown = await resp.json().catch(() => null);
  if (!resp.ok) {
    throw new Error(`worker ${resp.status}`);
  }
  if (!Array.isArray(parsed)) {
    throw new Error("invalid worker payload");
  }
  return parsed as AdminUserRow[];
}

export async function loadAdminUserOptions(supabase: SupabaseClient): Promise<AdminUserOption[]> {
  const accessToken = await getSupabaseAccessToken(supabase);
  if (!accessToken) return [];
  const rows = await loadAdminUsers(accessToken);
  return rows.map((u) => ({ id: u.id, email: u.email, full_name: u.full_name }));
}
