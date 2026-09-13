import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AppHeader } from "@/components/AppHeader";
import { PostSearchRunner } from "@/components/PostSearchRunner";
import { PromptForm } from "@/components/PromptForm";
import { JobSearchesPanel } from "@/components/jobs/JobSearchesPanel";
import { Link } from "@/i18n/navigation";
import { requireNotBlocked } from "@/lib/auth/blocked";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import type { UserProfileRow } from "@/types/database";

export default async function PromptsPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ tab?: string }>;
}) {
  const { locale } = await params;
  const { tab } = await searchParams;
  const t = await getTranslations("prompts");

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect(`/${locale}/login`);
  const isAdmin = await requireNotBlocked(supabase, data.user.id);

  const profileResp = await supabase
    .from("user_profiles_view")
    .select("*")
    .eq("id", data.user.id)
    .maybeSingle();

  const profile = (profileResp.data || null) as UserProfileRow | null;
  const activeTab = tab === "jobs" ? "jobs" : "posts";

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader
        title={t("title")}
        subtitle={data.user.email ?? null}
        active="prompts"
        isAdmin={isAdmin}
      />

      <main className="mx-auto max-w-3xl px-6 py-6">
        <div className="mb-6 flex gap-2">
          <Link
            href="/prompts"
            className={[
              "rounded-full border px-4 py-2 text-sm",
              activeTab === "posts"
                ? "border-border bg-card text-foreground"
                : "border-border/60 text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            {t("tabs.posts")}
          </Link>
          <Link
            href="/prompts?tab=jobs"
            className={[
              "rounded-full border px-4 py-2 text-sm",
              activeTab === "jobs"
                ? "border-border bg-card text-foreground"
                : "border-border/60 text-muted-foreground hover:text-foreground",
            ].join(" ")}
          >
            {t("tabs.jobs")}
          </Link>
        </div>

        {activeTab === "jobs" ? (
          <JobSearchesPanel
            initial={await (async () => {
              const { data: searches } = await supabase
                .from("job_searches")
                .select(
                  "id,title,search_query,location,filter_prompt,status,last_run_at,created_at,updated_at",
                )
                .eq("user_id", data.user.id)
                .order("created_at", { ascending: true });

              const rows = Array.isArray(searches) ? searches : [];
              const withCounts = await Promise.all(
                rows.map(async (s) => {
                  const lastRunAt = typeof s.last_run_at === "string" ? s.last_run_at : null;
                  if (!lastRunAt) return { ...s, new_match_count: 0 };
                  const { count } = await supabase
                    .from("job_analyses")
                    .select("id", { count: "exact", head: true })
                    .eq("job_search_id", s.id)
                    .eq("match", true)
                    .gte("analyzed_at", lastRunAt);
                  return { ...s, new_match_count: count ?? 0 };
                }),
              );
              return withCounts as any;
            })()}
          />
        ) : (
          <>
            <div className="overflow-hidden rounded-2xl border border-border bg-card">
              <div className="border-b border-border px-6 py-5">
                <div className="space-y-1">
                  <h2 className="text-lg font-semibold tracking-tight">{t("settings.title")}</h2>
                  <p className="max-w-xl text-sm leading-6 text-muted-foreground">
                    {t("settings.description")}
                  </p>
                </div>
              </div>

              <div className="p-6">
                <PromptForm initialProfile={profile} />
              </div>
            </div>

            <div className="mt-6 overflow-hidden rounded-2xl border border-border bg-card">
              <div className="border-b border-border px-6 py-5">
                <div className="space-y-1">
                  <h2 className="text-lg font-semibold tracking-tight">{t("run.title")}</h2>
                  <p className="max-w-xl text-sm leading-6 text-muted-foreground">
                    {t("run.description")}
                  </p>
                </div>
              </div>

              <div className="p-6">
                <PostSearchRunner />
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

