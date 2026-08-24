import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";

type Body = {
  full_name?: unknown;
  phone?: unknown;
  avatar_url?: unknown;
  company?: unknown;
  job_title?: unknown;
  date_of_birth?: unknown;
  city?: unknown;
  website?: unknown;
  bio?: unknown;
};

function toNullableTrimmedString(v: unknown) {
  if (typeof v !== "string") return null;
  const s = v.trim();
  return s || null;
}

function toNullableDateString(v: unknown) {
  if (typeof v !== "string") return null;
  const s = v.trim();
  return s || null;
}

export async function POST(request: Request) {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  let json: Body = {};
  try {
    json = (await request.json()) as Body;
  } catch {
    return NextResponse.json({ ok: false, error: "invalid json" }, { status: 400 });
  }

  const payload = {
    id: data.user.id,
    full_name: toNullableTrimmedString(json.full_name),
    phone: toNullableTrimmedString(json.phone),
    avatar_url: toNullableTrimmedString(json.avatar_url),
    company: toNullableTrimmedString(json.company),
    job_title: toNullableTrimmedString(json.job_title),
    date_of_birth: toNullableDateString(json.date_of_birth),
    city: toNullableTrimmedString(json.city),
    website: toNullableTrimmedString(json.website),
    bio: toNullableTrimmedString(json.bio),
    updated_at: new Date().toISOString(),
  };

  const { error } = await supabase.from("user_profiles").upsert(payload);
  if (error) {
    return NextResponse.json(
      { ok: false, error: error.message || "supabase error" },
      { status: 400 }
    );
  }

  return NextResponse.json({ ok: true }, { status: 200 });
}

