import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AppHeader } from "@/components/AppHeader";
import { AdminSectionTabs } from "@/components/admin/AdminSectionTabs";
import { AdminSearchesPanel } from "@/components/admin/AdminSearchesPanel";
import { loadAdminUserOptions } from "@/lib/admin/users";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export default async function AdminSearchesPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const tAdmin = await getTranslations("admin");

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

  const loc = locale === "en" ? "en" : "ru";
  const userOptions = await loadAdminUserOptions(supabase);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader title={tAdmin("title")} subtitle={data.user.email ?? null} active="admin" isAdmin />

      <main className="mx-auto max-w-5xl px-6 py-6">
        <AdminSectionTabs active="searches" />
        <AdminSearchesPanel locale={loc} initialUsers={userOptions} />
      </main>
    </div>
  );
}

