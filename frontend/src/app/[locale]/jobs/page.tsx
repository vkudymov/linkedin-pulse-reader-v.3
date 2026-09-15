import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { AppHeader } from "@/components/AppHeader";
import { type JobAnalysisRow, type JobRow } from "@/components/jobs/JobCard";
import { JobsResults } from "@/components/jobs/JobsResults";
import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import { requireNotBlocked } from "@/lib/auth/blocked";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { cn } from "@/lib/utils";

type Filter = "all" | "match" | "no_match";

function normalizeFilter(raw: unknown): Filter {
  if (raw === "match" || raw === "no_match" || raw === "all") return raw;
  return "all";
}

function stringFromRaw(raw: unknown, key: string): string | null {
  if (!raw || typeof raw !== "object") return null;
  const value = (raw as Record<string, unknown>)[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function stringsFromRaw(raw: unknown, key: string): string[] {
  if (!raw || typeof raw !== "object") return [];
  const value = (raw as Record<string, unknown>)[key];
  if (!Array.isArray(value)) return [];
  return value.filter((x): x is string => typeof x === "string" && x.trim().length > 0);
}

function asJob(job: unknown): JobRow | null {
  if (!job) return null;
  const row = (Array.isArray(job) ? job[0] : job) as JobRow | null;
  if (!row || typeof row !== "object") return null;
  const raw = (row as { raw_extra?: unknown }).raw_extra;
  return {
    ...row,
    company_url: row.company_url || stringFromRaw(raw, "company_url"),
    posted_at_text: row.posted_at_text || stringFromRaw(raw, "posted_at_text"),
    workplace_type: row.workplace_type || stringFromRaw(raw, "workplace_type"),
    employment_type: row.employment_type || stringFromRaw(raw, "employment_type"),
    insights: row.insights?.length ? row.insights : stringsFromRaw(raw, "insights"),
  };
}

export default async function JobsPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ search?: string; filter?: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("jobs.page");
  const { search: rawSearchId, filter: rawFilter } = await searchParams;
  const filter = normalizeFilter(rawFilter);

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect(`/${locale}/login`);
  const isAdmin = await requireNotBlocked(supabase, data.user.id);

  const searchesResp = await supabase
    .from("job_searches")
    .select("id,title,status")
    .eq("user_id", data.user.id)
    .order("created_at", { ascending: true });
  const searches = Array.isArray(searchesResp.data) ? searchesResp.data : [];

  const selectedId =
    typeof rawSearchId === "string" && rawSearchId
      ? rawSearchId
      : (searches[0]?.id as string | undefined);

  let rows: JobAnalysisRow[] = [];
  const counts = { all: 0, match: 0, noMatch: 0 };
  if (selectedId) {
    const resp = await supabase
      .from("job_analyses")
      .select(
        "match,score,reason,matched_requirements,missing_requirements,red_flags,error,analyzed_at,job:jobs(id,job_url,title,company,location,description,fetched_at,raw_extra)",
      )
      .eq("job_search_id", selectedId)
      .order("analyzed_at", { ascending: false })
      .limit(100);

    const allRows = (Array.isArray(resp.data) ? resp.data : []).map((r) => {
      const row = r as unknown as JobAnalysisRow;
      return {
        ...row,
        job: asJob((r as { job?: unknown }).job),
      };
    });
    counts.all = allRows.length;
    counts.match = allRows.filter((r) => r.match).length;
    counts.noMatch = allRows.filter((r) => !r.match).length;
    rows =
      filter === "match"
        ? allRows.filter((r) => r.match)
        : filter === "no_match"
          ? allRows.filter((r) => !r.match)
          : allRows;
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <AppHeader
        title={t("title")}
        subtitle={data.user.email ?? null}
        active="jobs"
        isAdmin={isAdmin}
      />

      <main className="mx-auto max-w-3xl px-6 py-6">
        {searches.length === 0 ? (
          <div className="rounded-2xl border border-border/80 bg-muted/40 px-6 py-5 text-sm text-muted-foreground">
            {t("emptySearches")}{" "}
            <Link className="underline-offset-4 hover:underline" href="/prompts?tab=jobs">
              {t("goToPrompts")}
            </Link>
          </div>
        ) : (
          <>
            <div className="mb-6 flex flex-wrap gap-2">
              {searches.map((s) => (
                <Link
                  key={s.id as string}
                  href={`/jobs?search=${encodeURIComponent(s.id as string)}&filter=${filter}`}
                  className={[
                    "rounded-full border px-4 py-2 text-sm",
                    (s.id as string) === selectedId
                      ? "border-border bg-card text-foreground"
                      : "border-border/60 text-muted-foreground hover:text-foreground",
                  ].join(" ")}
                >
                  {s.title as string}
                </Link>
              ))}
            </div>

            <JobsResults
              rows={rows}
              filters={
                <div className="inline-flex flex-wrap gap-2">
                  {(
                    [
                      ["all", t("filters.all"), counts.all],
                      ["match", t("filters.match"), counts.match],
                      ["no_match", t("filters.noMatch"), counts.noMatch],
                    ] as const
                  ).map(([value, label, count]) => {
                    const active = filter === value;
                    return (
                      <Link
                        key={value}
                        href={`/jobs?search=${encodeURIComponent(selectedId as string)}&filter=${value}`}
                        className={cn(
                          buttonVariants({
                            variant: active ? "default" : "outline",
                            size: "sm",
                          }),
                          "h-9 gap-2 rounded-full px-4",
                        )}
                      >
                        {label}
                        <span
                          className={cn(
                            "inline-flex min-w-5 items-center justify-center rounded-full px-1.5 text-xs tabular-nums",
                            active
                              ? "bg-primary-foreground/15 text-primary-foreground"
                              : "bg-muted text-muted-foreground",
                          )}
                        >
                          {count}
                        </span>
                      </Link>
                    );
                  })}
                </div>
              }
            />
          </>
        )}
      </main>
    </div>
  );
}

