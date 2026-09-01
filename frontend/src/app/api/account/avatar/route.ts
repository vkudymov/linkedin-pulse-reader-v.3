import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";

function extFromContentType(contentType: string | null) {
  const type = (contentType || "").toLowerCase();
  if (type === "image/png") return "png";
  if (type === "image/webp") return "webp";
  if (type === "image/jpeg" || type === "image/jpg") return "jpg";
  return null;
}

export async function POST(request: Request) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return NextResponse.json({ ok: false, error: "invalid form-data" }, { status: 400 });
  }

  const file = form.get("file");
  if (!(file instanceof File)) {
    return NextResponse.json({ ok: false, error: "missing file" }, { status: 400 });
  }

  if (file.size > 2 * 1024 * 1024) {
    return NextResponse.json({ ok: false, error: "file too large (max 2MB)" }, { status: 400 });
  }

  const ext = extFromContentType(file.type) || "jpg";
  const path = `${data.user.id}/avatar.${ext}`;
  const bytes = new Uint8Array(await file.arrayBuffer());

  // Delete previous avatars (e.g. avatar.jpg + avatar.webp) so only one stays.
  const { data: existing, error: listError } = await supabase.storage
    .from("avatars")
    .list(data.user.id, { limit: 100 });
  if (listError) {
    return NextResponse.json({ ok: false, error: listError.message || "list failed" }, { status: 400 });
  }

  const toDelete = (existing || [])
    .map((o) => o.name)
    .filter((name) => name.startsWith("avatar."))
    .map((name) => `${data.user.id}/${name}`);
  if (toDelete.length > 0) {
    const { error: removeError } = await supabase.storage.from("avatars").remove(toDelete);
    if (removeError) {
      return NextResponse.json(
        { ok: false, error: removeError.message || "delete failed" },
        { status: 400 },
      );
    }
  }

  const { error: uploadError } = await supabase.storage
    .from("avatars")
    .upload(path, bytes, { upsert: true, contentType: file.type || undefined });
  if (uploadError) {
    return NextResponse.json(
      { ok: false, error: uploadError.message || "upload failed" },
      { status: 400 },
    );
  }

  const { data: urlData } = supabase.storage.from("avatars").getPublicUrl(path);
  if (!urlData.publicUrl) {
    return NextResponse.json({ ok: false, error: "public url missing" }, { status: 500 });
  }

  // Persist avatar URL to user profile so it is shown on next page load.
  const { error: profileError } = await supabase
    .from("user_profiles")
    .upsert({ id: data.user.id, avatar_url: urlData.publicUrl, updated_at: new Date().toISOString() });
  if (profileError) {
    return NextResponse.json(
      { ok: false, error: profileError.message || "profile update failed" },
      { status: 400 },
    );
  }

  return NextResponse.json({ ok: true, publicUrl: urlData.publicUrl }, { status: 200 });
}

