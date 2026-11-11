"use client";

import { useRouter } from "next/navigation";
import { useState, type ComponentType } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Briefcase, Calendar, ChevronDown, ExternalLink, MapPin, Trash2, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Separator } from "@/components/ui/separator";
import { MatchInsightGrid } from "@/components/MatchInsightGrid";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { displayPersonHeadline, displayPersonName } from "@/lib/personDisplay";
import { cn } from "@/lib/utils";

export type PersonRow = {
  id: string;
  profile_url: string;
  full_name: string | null;
  avatar_url: string | null;
  headline: string | null;
  location: string | null;
  connection_degree: string | null;
  about: string | null;
  skills: string[] | null;
  current_company: string | null;
  fetched_at: string | null;
};

export type PersonAnalysisRow = {
  match: boolean;
  score: number;
  reason: string;
  matched_requirements: unknown;
  missing_requirements: unknown;
  red_flags: unknown;
  error: string | null;
  analyzed_at: string;
  person: PersonRow | null;
};

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

function asSkills(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((x): x is string => typeof x === "string" && x.trim().length > 0);
}

function initialsFromName(name: string | null | undefined) {
  const raw = (name || "").trim();
  if (!raw) return "?";
  const parts = raw.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
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

export function PersonCard({ row }: { row: PersonAnalysisRow }) {
  const router = useRouter();
  const locale = useLocale() === "en" ? "en" : "ru";
  const t = useTranslations("people.page");
  const { person } = row;
  const [open, setOpen] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [deletePending, setDeletePending] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (!person || deleted) return null;
  const current = person;
  const accepted = row.match === true;
  const analyzedAt = formatDateTime(row.analyzed_at, locale);
  const skills = asSkills(current.skills);
  const displayName = displayPersonName(current.full_name) || current.full_name || t("unnamed");
  const displayHeadline = displayPersonHeadline(current.headline, {
    name: displayName,
    location: current.location,
  });

  async function onDelete() {
    if (!current.id) return;
    if (!confirm(t("delete.confirm"))) return;
    setDeletePending(true);
    setDeleteError(null);
    try {
      const res = await fetch(`/api/people/${encodeURIComponent(current.id)}`, { method: "DELETE" });
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
          <div className="flex min-w-0 items-start gap-3">
            <Avatar size="lg" className="size-12">
              {current.avatar_url ? (
                <AvatarImage
                  src={current.avatar_url}
                  alt={displayName}
                  referrerPolicy="no-referrer"
                />
              ) : null}
              <AvatarFallback className="bg-background text-sm font-medium text-foreground">
                {initialsFromName(displayName)}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 space-y-1.5">
              <CardTitle className="text-base font-semibold leading-snug tracking-tight">{displayName}</CardTitle>
              {displayHeadline ? (
                <p className="line-clamp-2 text-xs font-normal leading-relaxed text-muted-foreground">
                  {displayHeadline}
                </p>
              ) : null}
            </div>
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
          {current.location ? (
            <MetaChip icon={MapPin} label={t("meta.location")} value={current.location} />
          ) : null}
          {current.current_company ? (
            <MetaChip icon={Briefcase} label={t("meta.company")} value={current.current_company} />
          ) : null}
          {current.connection_degree ? (
            <MetaChip icon={Users} label={t("meta.connection")} value={current.connection_degree} />
          ) : null}
          {analyzedAt ? (
            <MetaChip icon={Calendar} label={t("meta.analyzed")} value={analyzedAt} />
          ) : null}
        </div>

        {skills.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {skills.slice(0, 8).map((skill) => (
              <span
                key={skill}
                className="inline-flex items-center rounded-full border border-foreground/30 px-3 py-1 text-xs text-foreground"
              >
                {skill}
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

          <MatchInsightGrid
            matchedTitle={t("matched")}
            missingTitle={t("missing")}
            redFlagsTitle={t("redFlags")}
            matched={row.matched_requirements}
            missing={row.missing_requirements}
            redFlags={row.red_flags}
          />

          {!open && current.about ? (
            <p className="line-clamp-3 text-sm leading-6 text-foreground/85">{current.about}</p>
          ) : null}

          {!open && !current.about ? (
            <p className="text-sm italic text-muted-foreground">{t("contentUnavailable")}</p>
          ) : null}

          <CollapsibleContent>
            {current.about ? (
              <div className="whitespace-pre-wrap text-sm leading-6 text-foreground/90">{current.about}</div>
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
              {current.profile_url ? (
                <a
                  className={cn(
                    buttonVariants({ variant: "outline", size: "sm" }),
                    "h-9 rounded-full px-4",
                  )}
                  href={current.profile_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("actions.openLinkedIn")}
                  <ExternalLink className="size-3.5" />
                </a>
              ) : null}

              {current.id ? (
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
