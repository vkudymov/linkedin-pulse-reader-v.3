"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowDownWideNarrow, ArrowUpWideNarrow, Search } from "lucide-react";

import { PersonCard, type PersonAnalysisRow } from "@/components/people/PersonCard";
import {
  LinkedInFilterButton,
  LinkedInFilterLink,
  LinkedInFilterRow,
  LinkedInFilterSelect,
  linkedinFilterChipClass,
} from "@/components/ui/linkedin-filter-chip";
import { cn } from "@/lib/utils";

type SortField = "searched" | "score" | "name";
type SortDir = "desc" | "asc";

function timestampMs(value: string | null | undefined): number {
  if (!value) return 0;
  const ms = Date.parse(value);
  return Number.isNaN(ms) ? 0 : ms;
}

function searchedMs(row: PersonAnalysisRow): number {
  return timestampMs(row.analyzed_at) || timestampMs(row.person?.fetched_at);
}

function asSkills(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((x): x is string => typeof x === "string" && x.trim().length > 0);
}

function matchesQuery(row: PersonAnalysisRow, query: string): boolean {
  if (!query) return true;
  const person = row.person;
  const blob = [
    person?.full_name,
    person?.headline,
    person?.location,
    person?.about,
    person?.current_company,
    ...(asSkills(person?.skills)),
  ]
    .filter(Boolean)
    .join("\n")
    .toLowerCase();
  return blob.includes(query);
}

function topValues(values: string[], limit = 8): string[] {
  const counts = new Map<string, number>();
  for (const value of values) {
    const key = value.trim();
    if (!key) continue;
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit)
    .map(([value]) => value);
}

export function PeopleResults({
  rows,
  searchId,
  filter,
  counts,
}: {
  rows: PersonAnalysisRow[];
  searchId: string;
  filter: "all" | "match" | "no_match";
  counts: { all: number; match: number; noMatch: number };
}) {
  const t = useTranslations("people.page");
  const [query, setQuery] = useState("");
  const [sortField, setSortField] = useState<SortField>("searched");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [degree, setDegree] = useState<string>("all");
  const [location, setLocation] = useState<string>("all");
  const [skill, setSkill] = useState<string>("all");

  const normalizedQuery = query.trim().toLowerCase();
  const degrees = useMemo(
    () => topValues(rows.map((r) => r.person?.connection_degree || "").filter(Boolean)),
    [rows],
  );
  const locations = useMemo(
    () => topValues(rows.map((r) => r.person?.location || "").filter(Boolean)),
    [rows],
  );
  const skills = useMemo(
    () => topValues(rows.flatMap((r) => asSkills(r.person?.skills))),
    [rows],
  );

  const visible = useMemo(() => {
    const filtered = rows.filter((row) => {
      if (!matchesQuery(row, normalizedQuery)) return false;
      if (degree !== "all" && row.person?.connection_degree !== degree) return false;
      if (location !== "all" && row.person?.location !== location) return false;
      if (skill !== "all" && !asSkills(row.person?.skills).includes(skill)) return false;
      return true;
    });
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      if (sortField === "name") {
        const an = (a.person?.full_name || "").toLowerCase();
        const bn = (b.person?.full_name || "").toLowerCase();
        const cmp = an.localeCompare(bn);
        if (cmp !== 0) return cmp * dir;
      } else if (sortField === "score") {
        const delta = (Number.isFinite(a.score) ? a.score : 0) - (Number.isFinite(b.score) ? b.score : 0);
        if (delta !== 0) return delta * dir;
      } else {
        const delta = searchedMs(a) - searchedMs(b);
        if (delta !== 0) return delta * dir;
      }
      return searchedMs(b) - searchedMs(a);
    });
  }, [rows, normalizedQuery, sortField, sortDir, degree, location, skill]);

  return (
    <>
      <div className="mb-6 space-y-3">
        <LinkedInFilterRow>
          {(
            [
              ["all", t("filters.all"), counts.all],
              ["match", t("filters.match"), counts.match],
              ["no_match", t("filters.noMatch"), counts.noMatch],
            ] as const
          ).map(([value, label, count]) => (
            <LinkedInFilterLink
              key={value}
              href={`/people?search=${encodeURIComponent(searchId)}&filter=${value}`}
              active={filter === value}
              count={count}
            >
              {label}
            </LinkedInFilterLink>
          ))}
        </LinkedInFilterRow>
        {degrees.length || locations.length || skills.length ? (
          <LinkedInFilterRow>
            {degrees.map((value) => (
              <LinkedInFilterButton
                key={`deg-${value}`}
                active={degree === value}
                onClick={() => setDegree((cur) => (cur === value ? "all" : value))}
              >
                {value}
              </LinkedInFilterButton>
            ))}
            {locations.map((value) => (
              <LinkedInFilterButton
                key={`loc-${value}`}
                active={location === value}
                onClick={() => setLocation((cur) => (cur === value ? "all" : value))}
              >
                {value}
              </LinkedInFilterButton>
            ))}
            {skills.map((value) => (
              <LinkedInFilterButton
                key={`sk-${value}`}
                active={skill === value}
                onClick={() => setSkill((cur) => (cur === value ? "all" : value))}
              >
                {value}
              </LinkedInFilterButton>
            ))}
          </LinkedInFilterRow>
        ) : null}
        {rows.length > 0 ? (
          <div className="flex min-w-0 flex-wrap items-center gap-2 sm:max-w-md">
            <label className="relative min-w-[10rem] flex-1 sm:w-44">
              <span className="sr-only">{t("search.placeholder")}</span>
              <Search
                className="pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t("search.placeholder")}
                className={cn(
                  linkedinFilterChipClass(Boolean(query.trim())),
                  "h-8 w-full min-w-0 pl-9 font-normal outline-none placeholder:font-normal",
                  query.trim() ? "placeholder:text-white/70" : "placeholder:text-muted-foreground",
                )}
              />
            </label>
            <LinkedInFilterSelect
              value={sortField}
              active={sortField !== "searched" || sortDir !== "desc"}
              onChange={(e) => setSortField(e.target.value as SortField)}
              aria-label={t("sort.label")}
            >
              <option value="searched">{t("sort.searched")}</option>
              <option value="score">{t("sort.score")}</option>
              <option value="name">{t("sort.name")}</option>
            </LinkedInFilterSelect>
            <button
              type="button"
              onClick={() => setSortDir(sortDir === "desc" ? "asc" : "desc")}
              aria-label={sortDir === "desc" ? t("sort.desc") : t("sort.asc")}
              title={sortDir === "desc" ? t("sort.desc") : t("sort.asc")}
              className={cn(linkedinFilterChipClass(sortDir === "asc"), "size-8 justify-center px-0")}
            >
              {sortDir === "desc" ? (
                <ArrowDownWideNarrow className="size-4" aria-hidden />
              ) : (
                <ArrowUpWideNarrow className="size-4" aria-hidden />
              )}
            </button>
          </div>
        ) : null}
      </div>

      {rows.length === 0 ? (
        <div className="rounded-2xl border border-border/80 bg-muted/40 px-6 py-5 text-sm text-muted-foreground">
          {t("emptyResults")}
        </div>
      ) : visible.length === 0 ? (
        <div className="rounded-2xl border border-border/80 bg-muted/40 px-6 py-5 text-sm text-muted-foreground">
          {t("search.empty")}
        </div>
      ) : (
        <div className="space-y-4">
          {visible.map((r, idx) => (
            <PersonCard
              key={r.person?.id || `${r.person?.profile_url || "person"}-${r.analyzed_at || idx}`}
              row={r}
            />
          ))}
        </div>
      )}
    </>
  );
}
