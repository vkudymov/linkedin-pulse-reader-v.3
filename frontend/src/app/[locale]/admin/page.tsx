import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AppHeader } from "@/components/AppHeader";
import { AdminUsersTable } from "@/components/admin/AdminUsersTable";
import { createSupabaseServerClient } from "@/lib/supabase/server";

type AdminUserRow = {
  id: string;
  email: string | null;
  created_at: string | null;
  full_name: string | null;
  is_admin: boolean;
  is_blocked: boolean;
  blocked_at: string | null;
  post_search_run_count: number;
};

export default async function AdminPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("admin");

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect(`/${locale}/login`);

  const profileResp = await supabase
    .from("user_admin_state")
    .select("is_admin,is_blocked")
    .eq("id", data.user.id)
    .maybeSingle();

  const isAdmin = Boolean(profileResp.data?.is_admin);
  const isBlocked = Boolean(profileResp.data?.is_blocked);
  if (!isAdmin) redirect(`/${locale}/posts`);
  if (isBlocked) redirect(`/${locale}/login?blocked=1`);

  let users: AdminUserRow[] = [];
  let loadError: string | null = null;
  try {
    const { data: sessionData } = await supabase.auth.getSession();
    const accessToken = sessionData.session?.access_token ?? null;
    if (!accessToken) {
      loadError = "missing session";
    } else {
      const baseUrl = (process.env.WORKER_API_URL || "http://127.0.0.1:8000")
        .trim()
        .replace(/\/+$/, "");
      const resp = await fetch(`${baseUrl}/v1/admin/users`, {
        method: "GET",
        cache: "no-store",
        headers: { authorization: `Bearer ${accessToken}` },
      });
      const parsed: unknown = await resp.json().catch(() => null);
      if (resp.ok && Array.isArray(parsed)) {
        users = parsed as AdminUserRow[];
      } else if (!resp.ok) {
        loadError = `worker ${resp.status}`;
      } else {
        loadError = "invalid worker payload";
      }
    }
  } catch {
    users = [];
    loadError = "worker unreachable";
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader
        title={t("title")}
        subtitle={data.user.email ?? null}
        active="admin"
        isAdmin
      />

      <main className="mx-auto max-w-5xl px-6 py-6">
        <AdminUsersTable initialUsers={users} loadError={loadError} />
      </main>
    </div>
  );
}

