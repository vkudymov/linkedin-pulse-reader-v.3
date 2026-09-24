import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AppHeader } from "@/components/AppHeader";
import { AdminSectionTabs } from "@/components/admin/AdminSectionTabs";
import { AdminUsersTable } from "@/components/admin/AdminUsersTable";
import { loadAdminUsers, type AdminUserRow } from "@/lib/admin/users";
import { getSupabaseAccessToken } from "@/lib/admin/workerAccess";
import { createSupabaseServerClient } from "@/lib/supabase/server";

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
    const accessToken = await getSupabaseAccessToken(supabase);
    if (!accessToken) {
      loadError = "missing session";
    } else {
      users = await loadAdminUsers(accessToken);
    }
  } catch (e: unknown) {
    users = [];
    loadError = e instanceof Error ? e.message : "worker unreachable";
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
        <AdminSectionTabs active="users" />
        <AdminUsersTable initialUsers={users} loadError={loadError} />
      </main>
    </div>
  );
}

