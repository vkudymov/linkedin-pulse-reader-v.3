import { redirect } from "next/navigation";
import type { SupabaseClient } from "@supabase/supabase-js";

import type { UserProfileRow } from "@/types/database";

export async function requireNotBlocked(supabase: SupabaseClient, userId: string) {
  const profileResp = await supabase
    .from("user_admin_state")
    .select("is_blocked,is_admin")
    .eq("id", userId)
    .maybeSingle();
  const profile = (profileResp.data || null) as Pick<
    UserProfileRow,
    "is_blocked" | "is_admin"
  > | null;
  if (profile?.is_blocked) {
    redirect("/login?blocked=1");
  }
  return Boolean(profile?.is_admin);
}

