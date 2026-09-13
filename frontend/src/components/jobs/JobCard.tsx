"use client";

import { useRouter } from "next/navigation";
import { useState, type ComponentType } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Briefcase, Calendar, ChevronDown, ExternalLink, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Separator } from "@/components/ui/separator";
import { resolveJobInsights, stripInsightPhrases } from "@/lib/jobInsights";
import { cn } from "@/lib/utils";

export type JobRow = {
  id: string;
  job_url: string;
  title: string;
  company: string | null;
  company_url?: string | null;
  location: string | null;
  description: string | null;
  fetched_at: string | null;
  workplace_type?: string | null;
  employment_type?: string | null;
  insights?: string[];
};

export type JobAnalysisRow = {
  match: boolean;
  score: number;
  reason: string;
  matched_requirements: unknown;
  missing_requirements: unknown;
  red_flags: unknown;
  error: string | null;
  analyzed_at: string;
  job: JobRow | null;
};

function asStringList(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string" && x.trim().length > 0);
}

function companyPageHref(company: string, companyUrl: string | null | undefined): string {
  const raw = (companyUrl || "").trim();
  if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;
  if (raw.startsWith("/")) return `https://www.linkedin.com${raw}`;
  return `https://www.linkedin.com/search/results/companies/?keywords=${encodeURIComponent(company)}`;
}

function formatDateTime(value: string | null | undefined, locale: "ru" | "en"): string | null {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleString(locale === "en" ? "en-US" : "ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function MetaChip({
  icon: Icon,
  label,
  value,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"
      title={`${label}: ${value}`}
    >
      <Icon className="size-3.5 shrink-0 opacity-70" aria-hidden />
      <span className="tabular-nums">{value}</span>
    </span>
  );
}

export function JobCard({ row }: { row: JobAnalysisRow }) {
  const router = useRouter();
  const locale = useLocale() === "en" ? "en" : "ru";
  const t = useTranslations("jobs.page");
  const { job } = row;
  const [open, setOpen] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [deletePending, setDeletePending] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (!job || deleted) return null;
  const currentJob = job;

  const matched = asStringList(row.matched_requirements);
  const missing = asStringList(row.missing_requirements);
  const redFlags = asStringList(row.red_flags);
  const accepted = row.match === true;
  const analyzedAt = formatDateTime(row.analyzed_at, locale);
  const insightChips = resolveJobInsights({
    workplace_type: currentJob.workplace_type,
    employment_type: currentJob.employment_type,
    insights: currentJob.insights,
    location: currentJob.location,
    description: currentJob.description,
  });
  const subtitle = stripInsightPhrases(currentJob.location);
  const companyHref = currentJob.company
    ? companyPageHref(currentJob.company, currentJob.company_url)
    : null;

  async function onDelete() {
    if (!currentJob.id) return;
    if (!confirm(t("delete.confirm"))) return;
    setDeletePending(true);
    setDeleteError(null);
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(currentJob.id)}`, { method: "DELETE" });
      const json = (await res.json().catch(() => null)) as { ok?: boolean; error?: string } | null;
      if (!res.ok || !json?.ok) {
        throw new Error(json?.error || t("delete.failed"));
      }
      setDeleted(true);
      router.refresh();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : t("delete.failed");
      setDeleteError(message);
    } finally {
      setDeletePending(false);
    }
  }

  return (
    <Card className="overflow-hidden rounded-2xl border border-border bg-secondary py-0 shadow-none ring-0 transition-colors hover:border-foreground/20">
      <CardHeader className="gap-3 px-6 pb-0 pt-6">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <CardTitle className="text-base font-semibold leading-snug">{currentJob.title}</CardTitle>
            {subtitle ? (
              <CardDescription className="line-clamp-2 text-sm leading-5">{subtitle}</CardDescription>
            ) : null}
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1.5">
            <Badge
              variant={accepted ? "default" : "destructive"}
              className="rounded-full px-2.5 py-0.5"
            >
              {accepted ? t("status.accepted") : t("status.rejected")}
            </Badge>
            <div className="text-lg font-semibold tabular-nums">{row.score}%</div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
          {analyzedAt ? (
            <MetaChip icon={Calendar} label={t("meta.analyzed")} value={analyzedAt} />
          ) : null}
          {currentJob.company && companyHref ? (
            <a
              href={companyHref}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              title={`${t("meta.company")}: ${currentJob.company}`}
            >
              <Briefcase className="size-3.5 shrink-0 opacity-70" aria-hidden />
              <span>{currentJob.company}</span>
            </a>
          ) : null}
        </div>

        {insightChips.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {insightChips.map((chip) => (
              <span
                key={chip.key}
                className="inline-flex items-center rounded-full border border-foreground/30 px-4 py-1.5 text-sm text-foreground"
              >
                {t(`insights.${chip.key}` as `insights.${typeof chip.key}`)}
              </span>
            ))}
          </div>
        ) : null}
      </CardHeader>

      <Collapsible open={open} onOpenChange={setOpen}>
        <CardContent className="space-y-3 px-6 pb-6 pt-5">
          {row.error ? (
            <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {row.error}
            </div>
          ) : null}

          {row.reason ? (
            <blockquote className="rounded-xl border border-border bg-background/60 px-3.5 py-2.5 text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{t("reason")}: </span>
              {row.reason}
            </blockquote>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-3">
            <ReqList title={t("matched")} items={matched} />
            <ReqList title={t("missing")} items={missing} />
            <ReqList title={t("redFlags")} items={redFlags} />
          </div>

          {!open && currentJob.description ? (
            <p className="line-clamp-3 text-sm leading-6 text-foreground/85">{currentJob.description}</p>
          ) : null}

          {!open && !currentJob.description ? (
            <p className="text-sm italic text-muted-foreground">{t("contentUnavailable")}</p>
          ) : null}

          <CollapsibleContent>
            {currentJob.description ? (
              <div className="whitespace-pre-wrap text-sm leading-6 text-foreground/90">
                {currentJob.description}
              </div>
            ) : (
              <p className="text-sm italic text-muted-foreground">{t("contentUnavailable")}</p>
            )}
          </CollapsibleContent>

          <Separator />

          <div className="flex flex-wrap items-center justify-between gap-3">
            <CollapsibleTrigger
              className={cn(
                buttonVariants({ variant: "outline", size: "sm" }),
                "h-9 rounded-full px-4 text-muted-foreground hover:text-foreground",
              )}
            >
              <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
              {open ? t("actions.collapse") : t("actions.details")}
            </CollapsibleTrigger>

            <div className="flex flex-wrap items-center justify-end gap-2">
              {currentJob.job_url ? (
                <a
                  className={cn(
                    buttonVariants({ variant: "outline", size: "sm" }),
                    "h-9 rounded-full px-4",
                  )}
                  href={currentJob.job_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("actions.openLinkedIn")}
                  <ExternalLink className="size-3.5" />
                </a>
              ) : null}

              {currentJob.id ? (
                <button
                  type="button"
                  onClick={onDelete}
                  disabled={deletePending}
                  className={cn(
                    buttonVariants({ variant: "outline", size: "sm" }),
                    "h-9 rounded-full px-4 text-destructive hover:text-destructive",
                  )}
                >
                  {t("actions.delete")}
                  <Trash2 className="size-3.5" />
                </button>
              ) : null}
            </div>
          </div>

          {deleteError ? (
            <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {deleteError}
            </div>
          ) : null}
        </CardContent>
      </Collapsible>
    </Card>
  );
}

function ReqList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-xl border border-border/80 bg-background/40 px-4 py-3">
      <div className="text-sm font-medium">{title}</div>
      {items.length ? (
        <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
          {items.slice(0, 8).map((x) => (
            <li key={x} className="truncate">
              {x}
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-2 text-sm text-muted-foreground">—</div>
      )}
    </div>
  );
}
