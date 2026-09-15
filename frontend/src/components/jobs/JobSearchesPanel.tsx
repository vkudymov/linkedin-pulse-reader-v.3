"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { JobSearchRunButton } from "@/components/jobs/JobSearchRunButton";
import { LinkedInJobFiltersBar } from "@/components/jobs/LinkedInJobFiltersBar";
import {
  DEFAULT_LINKEDIN_JOB_FILTERS,
  normalizeLinkedInJobFilters,
  type LinkedInJobFilters,
} from "@/lib/linkedinJobFilters";
import { cn } from "@/lib/utils";

export type JobSearchDto = {
  id: string;
  title: string;
  search_query: string;
  location: string | null;
  filter_prompt: string;
  status: "active" | "paused" | string;
  last_run_at: string | null;
  linkedin_filters?: LinkedInJobFilters | Record<string, unknown> | null;
  new_match_count?: number;
};

const MARKER = "<<<JOB_TEXT>>>";

export function JobSearchesPanel({
  initial,
  supportsLinkedinFilters = true,
}: {
  initial: JobSearchDto[];
  supportsLinkedinFilters?: boolean;
}) {
  const t = useTranslations("jobs.prompts");
  const [items, setItems] = useState<JobSearchDto[]>(initial);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [location, setLocation] = useState("");
  const [filterPrompt, setFilterPrompt] = useState(
    `${t("defaultFilterPrompt")}\n\n${MARKER}\n`,
  );
  const [linkedinFilters, setLinkedinFilters] = useState<LinkedInJobFilters>(DEFAULT_LINKEDIN_JOB_FILTERS);

  const canCreate = useMemo(() => {
    return (
      title.trim().length > 0 &&
      searchQuery.trim().length > 0 &&
      filterPrompt.trim().length > 0 &&
      filterPrompt.includes(MARKER)
    );
  }, [title, searchQuery, filterPrompt]);

  async function refresh() {
    const resp = await fetch("/api/job-searches", { method: "GET" });
    const json = (await resp.json().catch(() => null)) as
      | { ok?: boolean; job_searches?: JobSearchDto[] }
      | null;
    if (!resp.ok || !json?.ok || !Array.isArray(json.job_searches)) {
      throw new Error(t("errors.loadFailed"));
    }
    setItems(json.job_searches);
  }

  async function create() {
    setPending(true);
    setError(null);
    try {
      const resp = await fetch("/api/job-searches", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title,
          search_query: searchQuery,
          location: location.trim() || null,
          filter_prompt: filterPrompt,
          linkedin_filters: linkedinFilters,
          status: "active",
        }),
      });
      const json = (await resp.json().catch(() => null)) as { ok?: boolean; error?: string } | null;
      if (!resp.ok || !json?.ok) throw new Error(json?.error || t("errors.saveFailed"));
      setTitle("");
      setSearchQuery("");
      setLocation("");
      setLinkedinFilters(DEFAULT_LINKEDIN_JOB_FILTERS);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function remove(id: string) {
    setPending(true);
    setError(null);
    try {
      const resp = await fetch(`/api/job-searches/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      const json = (await resp.json().catch(() => null)) as { ok?: boolean; error?: string } | null;
      if (!resp.ok || !json?.ok) throw new Error(json?.error || t("errors.deleteFailed"));
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.deleteFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-card p-6">
        <div className="space-y-1">
          <h3 className="text-base font-semibold">{t("create.title")}</h3>
          <p className="text-sm text-muted-foreground">{t("create.description")}</p>
        </div>

        <div className="mt-5 grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="job_title">{t("fields.title")}</Label>
            <Input id="job_title" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="job_query">{t("fields.searchQuery")}</Label>
            <Input
              id="job_query"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("fields.searchQueryPlaceholder")}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="job_location">{t("fields.location")}</Label>
            <Input
              id="job_location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder={t("fields.locationPlaceholder")}
            />
          </div>
          <LinkedInJobFiltersBar
            value={linkedinFilters}
            onChange={setLinkedinFilters}
            disabled={pending || !supportsLinkedinFilters}
          />
          {!supportsLinkedinFilters ? (
            <p className="text-xs text-muted-foreground">
              Фильтры LinkedIn не сохраняются, пока не применена миграция{" "}
              <code className="rounded bg-muted px-1 py-0.5">
                20260913180000_job_searches_linkedin_filters.sql
              </code>
              .
            </p>
          ) : null}
          <div className="grid gap-2">
            <Label htmlFor="job_filter">{t("fields.filterPrompt")}</Label>
            <Textarea
              id="job_filter"
              value={filterPrompt}
              onChange={(e) => setFilterPrompt(e.target.value)}
              rows={8}
            />
            <p className="text-xs text-muted-foreground">
              {t("fields.markerHint", { marker: MARKER })}
            </p>
          </div>

          {error ? <div className="text-sm text-destructive">{error}</div> : null}

          <Button type="button" onClick={create} disabled={pending || !canCreate} className="h-10 rounded-full">
            {pending ? t("create.pending") : t("create.submit")}
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="text-base font-semibold">{t("list.title")}</h3>

        {items.length === 0 ? (
          <div className="rounded-2xl border border-border/80 bg-muted/40 px-6 py-5 text-sm text-muted-foreground">
            {t("list.empty")}
          </div>
        ) : null}

        {items.map((s) => (
          <JobSearchCard
            key={s.id}
            item={s}
            busy={pending}
            onSaved={refresh}
            onRemove={remove}
            supportsLinkedinFilters={supportsLinkedinFilters}
          />
        ))}
      </div>
    </div>
  );
}

function JobSearchCard({
  item,
  busy,
  onSaved,
  onRemove,
  supportsLinkedinFilters,
}: {
  item: JobSearchDto;
  busy: boolean;
  onSaved: () => Promise<void>;
  onRemove: (id: string) => Promise<void>;
  supportsLinkedinFilters: boolean;
}) {
  const t = useTranslations("jobs.prompts");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [title, setTitle] = useState(item.title);
  const [searchQuery, setSearchQuery] = useState(item.search_query);
  const [location, setLocation] = useState(item.location ?? "");
  const [filterPrompt, setFilterPrompt] = useState(item.filter_prompt);
  const [linkedinFilters, setLinkedinFilters] = useState<LinkedInJobFilters>(
    normalizeLinkedInJobFilters(item.linkedin_filters),
  );

  useEffect(() => {
    setTitle(item.title);
    setSearchQuery(item.search_query);
    setLocation(item.location ?? "");
    setFilterPrompt(item.filter_prompt);
    setLinkedinFilters(normalizeLinkedInJobFilters(item.linkedin_filters));
  }, [item]);

  const matchCount = typeof item.new_match_count === "number" ? item.new_match_count : 0;
  const canSave =
    title.trim().length > 0 &&
    searchQuery.trim().length > 0 &&
    filterPrompt.trim().length > 0 &&
    filterPrompt.includes(MARKER);

  async function save() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const resp = await fetch(`/api/job-searches/${encodeURIComponent(item.id)}`, {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          title,
          search_query: searchQuery,
          location,
          filter_prompt: filterPrompt,
          ...(supportsLinkedinFilters ? { linkedin_filters: linkedinFilters } : {}),
        }),
      });
      const json = (await resp.json().catch(() => null)) as { ok?: boolean; error?: string } | null;

      if (!resp.ok || !json?.ok) throw new Error(json?.error || t("errors.saveFailed"));
      await onSaved();
      setSaved(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("errors.saveFailed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-card p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="text-base font-semibold">{item.title}</div>
          <div className="text-sm text-muted-foreground">
            {item.status === "paused" ? t("status.paused") : t("status.active")}
            {matchCount ? ` · ${t("list.newMatches", { count: matchCount })}` : ""}
          </div>
        </div>

        <JobSearchRunButton jobSearchId={item.id} disabled={busy || saving} onDone={onSaved} />
      </div>

      {!open ? (
        <button
          type="button"
          className={cn(
            buttonVariants({ variant: "outline", size: "sm" }),
            "mt-4 h-9 rounded-full px-4 text-muted-foreground hover:text-foreground",
          )}
          onClick={() => setOpen(true)}
        >
          <ChevronDown className="size-4" />
          {t("edit.toggle")}
        </button>
      ) : (
        <div className="mt-4 grid gap-4">
          <div className="grid gap-2">
            <Label>{t("fields.title")}</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} disabled={busy || saving} />
          </div>
          <div className="grid gap-2">
            <Label>{t("fields.searchQuery")}</Label>
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              disabled={busy || saving}
            />
          </div>
          <div className="grid gap-2">
            <Label>{t("fields.location")}</Label>
            <Input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              disabled={busy || saving}
            />
          </div>
          <LinkedInJobFiltersBar
            value={linkedinFilters}
            onChange={setLinkedinFilters}
            disabled={busy || saving}
          />
          <div className="grid gap-2">
            <Label>{t("fields.filterPrompt")}</Label>
            <Textarea
              value={filterPrompt}
              rows={8}
              onChange={(e) => setFilterPrompt(e.target.value)}
              disabled={busy || saving}
            />
            <p className="text-xs text-muted-foreground">{t("fields.markerHint", { marker: MARKER })}</p>
          </div>

          {error ? <div className="text-sm text-destructive">{error}</div> : null}
          {saved ? <div className="text-sm text-emerald-600 dark:text-emerald-300">{t("edit.saved")}</div> : null}

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              className="h-9 rounded-full px-4 text-muted-foreground hover:text-foreground"
              onClick={() => setOpen(false)}
              disabled={saving}
            >
              <ChevronUp className="size-4" />
              {t("edit.collapse")}
            </Button>
            <Button
              type="button"
              className="h-9 rounded-full"
              onClick={save}
              disabled={busy || saving || !canSave}
            >
              {saving ? t("edit.saving") : t("edit.save")}
            </Button>
            <Button
              type="button"
              variant="destructive"
              className="h-9 rounded-full"
              onClick={() => onRemove(item.id)}
              disabled={busy || saving}
            >
              {t("edit.delete")}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

