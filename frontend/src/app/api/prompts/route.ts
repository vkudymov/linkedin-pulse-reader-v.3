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

export async function GET(request: Request) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  const url = new URL(request.url);
  const role = url.searchParams.get("role") || "";
  const id = (url.searchParams.get("id") || "").trim();
  const q = (url.searchParams.get("q") || "").trim();
  const limit = Math.max(1, Math.min(200, Number(url.searchParams.get("limit") || "50") || 50));
  const offset = Math.max(0, Number(url.searchParams.get("offset") || "0") || 0);

  let req = supabase
    .from("prompts")
    .select("id,user_id,role,title,body,created_at,updated_at", { count: "exact" })
    .eq("user_id", data.user.id);
  if (id) req = req.eq("id", id);
  if (role === "filter" || role === "search" || role === "comment") req = req.eq("role", role);
  if (q) req = req.or(`title.ilike.%${q}%,body.ilike.%${q}%`);
  const resp = await req.order("updated_at", { ascending: false }).range(offset, offset + limit - 1);
  if (resp.error) return Response.json({ ok: false, error: resp.error.message }, { status: 400 });
  const items = Array.isArray(resp.data) ? resp.data : [];
  return Response.json({ items, total: resp.count ?? items.length, limit, offset });
}

export async function POST(request: Request) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) return new Response("unauthorized", { status: 401 });

  let json: unknown = null;
  try {
    json = await request.json();
  } catch {
    return new Response("invalid json", { status: 400 });
  }
  const body = (json && typeof json === "object" ? json : {}) as Record<string, unknown>;
  const role = body.role === "filter" || body.role === "search" || body.role === "comment" ? body.role : "";
  const title = typeof body.title === "string" ? body.title.trim() : "";
  const text = typeof body.body === "string" ? body.body : "";
  if (!role || !title || !text.trim()) return Response.json({ ok: false, error: "invalid payload" }, { status: 400 });
  const invalid = validatePrompt(role, text);
  if (invalid) return Response.json({ ok: false, error: invalid }, { status: 400 });

  const created = await supabase
    .from("prompts")
    .insert({ user_id: data.user.id, role, title, body: text })
    .select("id,user_id,role,title,body,created_at,updated_at")
    .maybeSingle();
  if (created.error || !created.data) {
    return Response.json({ ok: false, error: created.error?.message || "create failed" }, { status: 400 });
  }
  return Response.json({ ok: true, prompt: created.data });
}
