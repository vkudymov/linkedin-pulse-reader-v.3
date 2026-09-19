import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AppHeader } from "@/components/AppHeader";
import { JobSearchesPanel } from "@/components/jobs/JobSearchesPanel";
import { PostSearchesPanel } from "@/components/posts/PostSearchesPanel";
import type { JobSearchDto } from "@/components/jobs/JobSearchesPanel";
import type { PostSearchDto } from "@/components/posts/PostSearchesPanel";
import { Link } from "@/i18n/navigation";
import { requireNotBlocked } from "@/lib/auth/blocked";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { loadJobSearchRows } from "@/lib/jobSearches";

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
  const activeTab = tab === "jobs" ? "jobs" : "posts";

  let jobSearchesInitial: JobSearchDto[] = [];
  let postSearchesInitial: PostSearchDto[] = [];
  let supportsLinkedinFilters = false;
  if (activeTab === "jobs") {
    const { rows, usedFiltersColumn } = await loadJobSearchRows(supabase, data.user.id);
    supportsLinkedinFilters = usedFiltersColumn;
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
    jobSearchesInitial = withCounts as JobSearchDto[];
  }
  if (activeTab === "posts") {
    const postSearchesResp = await supabase
      .from("post_searches")
      .select("id,user_id,title,search_prompt,comment_prompt,account_label,status,last_run_at,created_at,updated_at")
      .eq("user_id", data.user.id)
      .order("created_at", { ascending: true });
    postSearchesInitial = (postSearchesResp.data || []) as PostSearchDto[];
  }

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
          <JobSearchesPanel initial={jobSearchesInitial} supportsLinkedinFilters={supportsLinkedinFilters} />
        ) : (
          <PostSearchesPanel initial={postSearchesInitial} />
        )}
      </main>
    </div>
  );
}

