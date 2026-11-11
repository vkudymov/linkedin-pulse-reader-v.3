import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";
import { AppHeader } from "@/components/AppHeader";
import { type PersonAnalysisRow, type PersonRow } from "@/components/people/PersonCard";
import { PeopleResults } from "@/components/people/PeopleResults";
import { LinkedInFilterLink, LinkedInFilterRow } from "@/components/ui/linkedin-filter-chip";
import { requireNotBlocked } from "@/lib/auth/blocked";
import { attachSearchTariff, loadSearchTariffs } from "@/lib/searchTariffs";
import { loadPeopleSearchRows } from "@/lib/peopleSearches";
import { createSupabaseServerClient } from "@/lib/supabase/server";

type Filter = "all" | "match" | "no_match";

function normalizeFilter(raw: unknown): Filter {
  if (raw === "match" || raw === "no_match" || raw === "all") return raw;
  return "all";
}

function asSkills(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((x): x is string => typeof x === "string" && x.trim().length > 0);
}

function asPerson(person: unknown): PersonRow | null {
  if (!person) return null;
  const row = (Array.isArray(person) ? person[0] : person) as PersonRow | null;
  if (!row || typeof row !== "object") return null;
  return {
    ...row,
    avatar_url:
      typeof row.avatar_url === "string" && row.avatar_url.trim() ? row.avatar_url.trim() : null,
    skills: asSkills(row.skills),
  };
}

export default async function PeoplePage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ search?: string; filter?: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations("people.page");
  const { search: rawSearchId, filter: rawFilter } = await searchParams;
  const filter = normalizeFilter(rawFilter);

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();
  if (!data.user) redirect(`/${locale}/login`);
  const isAdmin = await requireNotBlocked(supabase, data.user.id);

  const loaded = await loadPeopleSearchRows(supabase, data.user.id);
  const tariffs = await loadSearchTariffs(supabase);
  const searches = (loaded.rows || []).map((row) => attachSearchTariff(row, tariffs));

  const selectedId =
    typeof rawSearchId === "string" && rawSearchId
      ? rawSearchId
      : (searches[0]?.id as string | undefined);

  let rows: PersonAnalysisRow[] = [];
  const counts = { all: 0, match: 0, noMatch: 0 };
  if (selectedId) {
    const resp = await supabase
      .from("people_analyses")
      .select(
        "match,score,reason,matched_requirements,missing_requirements,red_flags,error,analyzed_at,person:people(id,profile_url,full_name,avatar_url,headline,location,connection_degree,about,skills,current_company,fetched_at)",
      )
      .eq("search_id", selectedId)
      .order("analyzed_at", { ascending: false })
      .limit(100);

    const allRows = (Array.isArray(resp.data) ? resp.data : []).map((r) => {
      const row = r as unknown as PersonAnalysisRow;
      return {
        ...row,
        person: asPerson((r as { person?: unknown }).person),
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
        active="people"
        isAdmin={isAdmin}
      />

      <main className="mx-auto max-w-3xl px-6 py-6">
        {searches.length === 0 ? (
          <div className="rounded-2xl border border-border/80 bg-muted/40 px-6 py-5 text-sm text-muted-foreground">
            {t("emptySearches")}{" "}
            <Link className="underline-offset-4 hover:underline" href={{ pathname: "/searches", query: { type: "people" } }}>
              {t("goToSearches")}
            </Link>
          </div>
        ) : (
          <>
            <LinkedInFilterRow className="mb-6">
              {searches.map((s) => (
                <LinkedInFilterLink
                  key={String(s.id)}
                  href={`/people?search=${encodeURIComponent(String(s.id))}&filter=${filter}`}
                  active={String(s.id) === selectedId}
                >
                  {String(s.title)}
                </LinkedInFilterLink>
              ))}
            </LinkedInFilterRow>

            <PeopleResults
              rows={rows}
              searchId={selectedId as string}
              filter={filter}
              counts={counts}
            />
          </>
        )}
      </main>
    </div>
  );
}
