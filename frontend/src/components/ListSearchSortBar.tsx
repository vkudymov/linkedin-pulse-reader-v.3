"use client";

import { ArrowDownWideNarrow, ArrowUpWideNarrow, Search } from "lucide-react";

import { Input } from "@/components/ui/input";
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
  return (
    <div className="flex min-w-0 items-center gap-2 sm:max-w-md">
      <label className="relative min-w-0 flex-1 sm:w-44">
        <span className="sr-only">{labels.placeholder}</span>
        <Search
          className="pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <Input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder={labels.placeholder}
          className="h-9 rounded-full border-border bg-background pr-3 pl-9 dark:bg-background"
        />
      </label>

      <select
        value={sortField}
        onChange={(e) => onSortFieldChange(e.target.value as ListSortField)}
        aria-label={labels.sortLabel}
        className={cn(
          "h-9 shrink-0 rounded-full border border-border bg-background px-3 text-sm text-foreground",
          "outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
        )}
      >
        <option value="posted">{labels.posted}</option>
        <option value="searched">{labels.searched}</option>
        <option value="score">{labels.score}</option>
      </select>

      <button
        type="button"
        onClick={() => onSortDirChange(sortDir === "desc" ? "asc" : "desc")}
        aria-label={sortDir === "desc" ? labels.desc : labels.asc}
        title={sortDir === "desc" ? labels.desc : labels.asc}
        className={cn(
          "inline-flex size-9 shrink-0 items-center justify-center rounded-full border border-border bg-background text-foreground",
          "outline-none hover:bg-muted focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
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
