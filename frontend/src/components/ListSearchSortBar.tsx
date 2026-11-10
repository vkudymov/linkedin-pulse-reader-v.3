"use client";

import { ArrowDownWideNarrow, ArrowUpWideNarrow, Search } from "lucide-react";

import {
  LinkedInFilterSelect,
  linkedinFilterChipClass,
} from "@/components/ui/linkedin-filter-chip";
import { cn } from "@/lib/utils";

export type ListSortField = "posted" | "searched" | "score";
export type ListSortDir = "desc" | "asc";

export type ListSearchSortLabels = {
  placeholder: string;
  sortLabel: string;
  posted: string;
  searched: string;
  score: string;
  desc: string;
  asc: string;
};

export function ListSearchSortBar({
  query,
  onQueryChange,
  sortField,
  onSortFieldChange,
  sortDir,
  onSortDirChange,
  labels,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  sortField: ListSortField;
  onSortFieldChange: (value: ListSortField) => void;
  sortDir: ListSortDir;
  onSortDirChange: (value: ListSortDir) => void;
  labels: ListSearchSortLabels;
}) {
  const sortActive = sortField !== "searched" || sortDir !== "desc";

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-2 sm:max-w-md">
      <label className="relative min-w-[10rem] flex-1 sm:w-44">
        <span className="sr-only">{labels.placeholder}</span>
        <Search
          className="pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder={labels.placeholder}
          className={cn(
            linkedinFilterChipClass(Boolean(query.trim())),
            "h-8 w-full min-w-0 pl-9 font-normal outline-none placeholder:font-normal",
            query.trim() ? "placeholder:text-white/70" : "placeholder:text-muted-foreground",
          )}
        />
      </label>

      <LinkedInFilterSelect
        value={sortField}
        active={sortActive}
        onChange={(e) => onSortFieldChange(e.target.value as ListSortField)}
        aria-label={labels.sortLabel}
      >
        <option value="posted">{labels.posted}</option>
        <option value="searched">{labels.searched}</option>
        <option value="score">{labels.score}</option>
      </LinkedInFilterSelect>

      <button
        type="button"
        onClick={() => onSortDirChange(sortDir === "desc" ? "asc" : "desc")}
        aria-label={sortDir === "desc" ? labels.desc : labels.asc}
        title={sortDir === "desc" ? labels.desc : labels.asc}
        className={cn(
          linkedinFilterChipClass(sortDir === "asc"),
          "size-8 justify-center px-0",
        )}
      >
        {sortDir === "desc" ? (
          <ArrowDownWideNarrow className="size-4" aria-hidden />
        ) : (
          <ArrowUpWideNarrow className="size-4" aria-hidden />
        )}
      </button>
    </div>
  );
}
