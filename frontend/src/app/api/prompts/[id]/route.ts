import { createSupabaseServerClient } from "@/lib/supabase/server";

const JOB_MARKER = "<<<JOB_TEXT>>>";
const SEARCH_MARKER = "<<<POST_TEXT>>>";
const COMMENT_MARKERS = ["<<<POST_TEXT>>>", "<<<CONTENT_TYPE>>>", "<<<MAIN_TOPICS>>>", "<<<TARGET_LANGUAGE>>>"];

function validatePrompt(role: string, body: string): string | null {
  if (!body.trim()) return "body is required";
  if (role === "filter" && !body.includes(JOB_MARKER)) return `body must contain ${JOB_MARKER}`;
  if (role === "search" && !body.includes(SEARCH_MARKER)) return `body must contain ${SEARCH_MARKER}`;
  if (role === "comment") {
    const missing = COMMENT_MARKERS.filter((m) => !body.includes(m));
    if (missing.length) return `body must contain markers: ${missing.join(", ")}`;
  }
  return null;
}

export async function PATCH(request: Request, ctx: { params: Promise<{ id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });
  const { id } = await ctx.params;

  const exists = await supabase
    .from("prompts")
    .select("id,role")
    .eq("id", id)
    .eq("user_id", data.user.id)
    .maybeSingle();
  if (exists.error || !exists.data) return new Response("not found", { status: 404 });

  let json: unknown = null;
  try {
    json = await request.json();
  } catch {
    return new Response("invalid json", { status: 400 });
  }
  const body = (json && typeof json === "object" ? json : {}) as Record<string, unknown>;
  const role = exists.data.role as string;
  const patch: Record<string, unknown> = { updated_at: new Date().toISOString() };
  if (typeof body.title === "string") {
    const title = body.title.trim();
    if (!title) return Response.json({ ok: false, error: "title is required" }, { status: 400 });
    patch.title = title;
  }
  if (typeof body.body === "string") {
    const invalid = validatePrompt(role, body.body);
    if (invalid) return Response.json({ ok: false, error: invalid }, { status: 400 });
    patch.body = body.body;
  }

  const updated = await supabase
    .from("prompts")
    .update(patch)
    .eq("id", id)
    .eq("user_id", data.user.id)
    .select("id,user_id,role,title,body,created_at,updated_at")
    .maybeSingle();
  if (updated.error || !updated.data) {
    return Response.json({ ok: false, error: updated.error?.message || "update failed" }, { status: 400 });
  }
  return Response.json(updated.data);
}

export async function DELETE(_request: Request, ctx: { params: Promise<{ id: string }> }) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });
  const { id } = await ctx.params;
  const exists = await supabase.from("prompts").select("id").eq("id", id).eq("user_id", data.user.id).maybeSingle();
  if (exists.error || !exists.data) return new Response("not found", { status: 404 });
  const resp = await supabase.from("prompts").delete().eq("id", id).eq("user_id", data.user.id);
  if (resp.error) return Response.json({ ok: false, error: resp.error.message }, { status: 400 });
  return Response.json({ ok: true });
}
