import { Suspense } from "react";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AppHeader } from "@/components/AppHeader";
import { UserSearchesPanel } from "@/components/searches/UserSearchesPanel";
import { requireNotBlocked } from "@/lib/auth/blocked";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export default async function SearchesPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("userSearches");

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect(`/${locale}/login`);
  const isAdmin = await requireNotBlocked(supabase, data.user.id);
  const loc = locale === "en" ? "en" : "ru";

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader title={t("title")} subtitle={data.user.email ?? null} active="searches" isAdmin={isAdmin} />

      <main className="mx-auto max-w-5xl px-6 py-6">
        <Suspense>
          <UserSearchesPanel locale={loc} />
        </Suspense>
      </main>
    </div>
  );
}
