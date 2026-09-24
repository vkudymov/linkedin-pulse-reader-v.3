import type { SupabaseClient } from "@supabase/supabase-js";

export type PromptRole = "filter" | "search" | "comment";

function titleFromBody(body: string, role: PromptRole, fallback?: string) {
  const first = body.split("\n", 1)[0]?.trim() || "";
  if (first) return first.slice(0, 80);
  return fallback || `${role} prompt`;
}

export async function createOwnedPrompt(
  supabase: SupabaseClient,
  userId: string,
  role: PromptRole,
  body: string,
  title?: string,
) {
  return supabase
    .from("prompts")
    .insert({
      user_id: userId,
      role,
      title: titleFromBody(body, role, title),
      body,
    })
    .select("id")
    .maybeSingle();
}

export async function updateOwnedPromptBody(
  supabase: SupabaseClient,
  userId: string,
  promptId: string,
  body: string,
) {
  return supabase
    .from("prompts")
    .update({ body, updated_at: new Date().toISOString() })
    .eq("id", promptId)
    .eq("user_id", userId);
}

export async function requireOwnedPrompt(
  supabase: SupabaseClient,
  userId: string,
  promptId: string,
  role: PromptRole,
) {
  const resp = await supabase
    .from("prompts")
    .select("id,role")
    .eq("id", promptId)
    .eq("user_id", userId)
    .maybeSingle();
  if (resp.error || !resp.data || resp.data.role !== role) return null;
  return resp.data.id as string;
}
