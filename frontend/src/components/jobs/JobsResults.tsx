"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import { JobCard, type JobAnalysisRow } from "@/components/jobs/JobCard";
import {
  ListSearchSortBar,
  type ListSortDir,
  type ListSortField,
} from "@/components/ListSearchSortBar";
import { LinkedInFilterLink, LinkedInFilterRow } from "@/components/ui/linkedin-filter-chip";
import { parseJobPostedAtMs } from "@/lib/parseJobPostedAt";

function timestampMs(value: string | null | undefined): number {
  if (!value) return 0;
  const ms = Date.parse(value);
  return Number.isNaN(ms) ? 0 : ms;
}

function postedMs(row: JobAnalysisRow): number {
  return parseJobPostedAtMs(row.job?.posted_at_text) ?? timestampMs(row.job?.fetched_at);
}

function searchedMs(row: JobAnalysisRow): number {
  return timestampMs(row.analyzed_at) || timestampMs(row.job?.fetched_at);
}

function sortValue(row: JobAnalysisRow, field: ListSortField): number {
  if (field === "score") return Number.isFinite(row.score) ? row.score : 0;
  if (field === "posted") return postedMs(row);
  return searchedMs(row);
}

function matchesQuery(row: JobAnalysisRow, query: string): boolean {
  if (!query) return true;
  const title = row.job?.title ?? "";
  const description = row.job?.description ?? "";
  return `${title}\n${description}`.toLowerCase().includes(query);
}

export function JobsResults({
  rows,
  searchId,
  filter,
  counts,
}: {
  rows: JobAnalysisRow[];
  searchId: string;
  filter: "all" | "match" | "no_match";
  counts: { all: number; match: number; noMatch: number };
}) {
  const t = useTranslations("jobs.page");
  const [query, setQuery] = useState("");
  const [sortField, setSortField] = useState<ListSortField>("searched");
  const [sortDir, setSortDir] = useState<ListSortDir>("desc");

  const normalizedQuery = query.trim().toLowerCase();

  const visible = useMemo(() => {
    const filtered = rows.filter((row) => matchesQuery(row, normalizedQuery));
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const delta = sortValue(a, sortField) - sortValue(b, sortField);
      if (delta !== 0) return delta * dir;
      return searchedMs(b) - searchedMs(a);
    });
  }, [rows, normalizedQuery, sortField, sortDir]);

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
              href={`/jobs?search=${encodeURIComponent(searchId)}&filter=${value}`}
              active={filter === value}
              count={count}
            >
              {label}
            </LinkedInFilterLink>
          ))}
        </LinkedInFilterRow>
        {rows.length > 0 ? (
          <ListSearchSortBar
            query={query}
            onQueryChange={setQuery}
            sortField={sortField}
            onSortFieldChange={setSortField}
            sortDir={sortDir}
            onSortDirChange={setSortDir}
            labels={{
              placeholder: t("search.placeholder"),
              sortLabel: t("sort.label"),
              posted: t("sort.posted"),
              searched: t("sort.searched"),
              score: t("sort.score"),
              desc: t("sort.desc"),
              asc: t("sort.asc"),
            }}
          />
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
            <JobCard key={`${r.job?.id ?? r.job?.job_url ?? "job"}-${idx}`} row={r} />
          ))}
        </div>
      )}
    </>
  );
}
