"use client";

import { useState, type ComponentType } from "react";
import {
  Calendar,
  ChevronDown,
  ExternalLink,
  Heart,
  ImageIcon,
  MessageCircle,
  Sparkles,
} from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
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
import { cn } from "@/lib/utils";
import { FeedPostRow } from "@/types/database";

type PostStatus = {
  label: string;
  badgeVariant: "default" | "secondary" | "destructive" | "outline";
};

function postStatus(post: FeedPostRow): PostStatus {
  if (post.is_relevant === true) {
    return { label: "принято", badgeVariant: "default" };
  }
  if (post.is_relevant === false) {
    return { label: "отклонено", badgeVariant: "destructive" };
  }
  return { label: "не проверено", badgeVariant: "secondary" };
}

function getReason(post: FeedPostRow): string | null {
  if (post.analysis_error) return post.analysis_error;
  const payload = post.analysis_payload;
  const reason = payload?.reason;
  return typeof reason === "string" && reason.trim() ? reason.trim() : null;
}

function authorInitials(name: string | null): string {
  if (!name?.trim()) return "?";
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function formatMetaDate(post: FeedPostRow): string | null {
  if (post.published_at_text?.trim()) return post.published_at_text.trim();
  if (post.fetched_at) {
    return new Date(post.fetched_at).toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "short",
    });
  }
  return null;
}

function formatCount(value: number | null): string | null {
  if (typeof value !== "number" || value < 0) return null;
  return value.toLocaleString("ru-RU");
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

function InsightPreview({
  title,
  text,
}: {
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-background/50 px-3.5 py-2.5">
      <p className="text-xs font-medium text-muted-foreground">{title}</p>
      <p className="mt-1 line-clamp-2 text-sm leading-5 text-foreground/90">{text}</p>
    </div>
  );
}

export function PostCard({ post }: { post: FeedPostRow }) {
  const [open, setOpen] = useState(false);
  const status = postStatus(post);
  const authorName = post.author_json?.name || null;
  const authorHeadline = post.author_json?.headline || null;
  const authorProfileUrl =
    typeof post.author_json?.profile_url === "string" &&
    post.author_json.profile_url.trim()
      ? post.author_json.profile_url.trim()
      : null;
  const reason = getReason(post);
  const comment =
    typeof post.comment_text === "string" && post.comment_text.trim()
      ? post.comment_text.trim()
      : null;
  const metaDate = formatMetaDate(post);
  const displayName = authorName || "Автор неизвестен";
  const reactions = formatCount(post.reactions_count);
  const comments = formatCount(post.comments_count);
  const hasMedia = post.media_urls.length > 0;
  const analyzedAt = post.analyzed_at
    ? new Date(post.analyzed_at).toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <Card className="overflow-hidden rounded-2xl border border-border bg-secondary py-0 shadow-none ring-0 transition-colors hover:border-foreground/20">
      <CardHeader className="gap-3 px-6 pb-0 pt-6">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-start gap-3">
            <Avatar size="default" className="size-10">
              <AvatarFallback className="bg-background text-sm font-medium text-foreground">
                {authorInitials(authorName)}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 space-y-1">
              <CardTitle className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-base font-semibold leading-snug">
                <span className="truncate">{displayName}</span>
                {authorProfileUrl ? (
                  <a
                    className="text-xs font-normal text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                    href={authorProfileUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Профиль
                  </a>
                ) : null}
              </CardTitle>
              {authorHeadline ? (
                <CardDescription className="line-clamp-2 text-sm leading-5">
                  {authorHeadline}
                </CardDescription>
              ) : null}
            </div>
          </div>
          <Badge variant={status.badgeVariant} className="shrink-0 rounded-full px-2.5 py-0.5">
            {status.label}
          </Badge>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
          {metaDate ? <MetaChip icon={Calendar} label="Дата" value={metaDate} /> : null}
          {reactions ? (
            <MetaChip icon={Heart} label="Реакции" value={reactions} />
          ) : null}
          {comments ? (
            <MetaChip icon={MessageCircle} label="Комментарии" value={comments} />
          ) : null}
          {hasMedia ? (
            <MetaChip
              icon={ImageIcon}
              label="Медиа"
              value={String(post.media_urls.length)}
            />
          ) : null}
          {analyzedAt ? (
            <MetaChip icon={Sparkles} label="Проанализировано" value={analyzedAt} />
          ) : null}
        </div>
      </CardHeader>

      <Collapsible open={open} onOpenChange={setOpen}>
        <CardContent className="space-y-3 px-6 pb-6 pt-5">
          {!open && post.content ? (
            <p className="line-clamp-3 text-sm leading-6 text-foreground/85">{post.content}</p>
          ) : null}

          {!open && !post.content ? (
            <p className="text-sm italic text-muted-foreground">Текст поста недоступен</p>
          ) : null}

          {!open && reason ? (
            <InsightPreview title="Причина отбора" text={reason} />
          ) : null}

          {!open && comment ? (
            <InsightPreview title="Черновик комментария" text={comment} />
          ) : null}

          <CollapsibleContent className="space-y-4">
            {post.content ? (
              <div className="whitespace-pre-wrap text-sm leading-6 text-foreground/90">
                {post.content}
              </div>
            ) : (
              <p className="text-sm italic text-muted-foreground">Текст поста недоступен</p>
            )}

            {reason ? (
              <blockquote className="rounded-xl border border-border bg-background/60 px-3.5 py-2.5 text-sm text-muted-foreground">
                <span className="font-medium text-foreground">Причина отбора: </span>
                {reason}
              </blockquote>
            ) : null}

            {comment ? (
              <div className="rounded-xl border border-border bg-background/60 px-3.5 py-2.5 text-sm">
                <div className="text-xs font-medium text-muted-foreground">
                  Черновик комментария
                </div>
                <div className="mt-1 whitespace-pre-wrap text-foreground/90">{comment}</div>
              </div>
            ) : null}

            <div className="grid gap-2 rounded-xl border border-border bg-background/40 p-3 text-xs text-muted-foreground sm:grid-cols-2">
              {post.published_at_text ? (
                <div>
                  <span className="font-medium text-foreground/80">Опубликовано</span>
                  <div className="mt-0.5">{post.published_at_text}</div>
                </div>
              ) : null}
              {post.fetched_at ? (
                <div>
                  <span className="font-medium text-foreground/80">Загружено</span>
                  <div className="mt-0.5">
                    {new Date(post.fetched_at).toLocaleString("ru-RU")}
                  </div>
                </div>
              ) : null}
              {analyzedAt ? (
                <div>
                  <span className="font-medium text-foreground/80">Анализ</span>
                  <div className="mt-0.5">{analyzedAt}</div>
                </div>
              ) : null}
              {post.source_key ? (
                <div>
                  <span className="font-medium text-foreground/80">Источник</span>
                  <div className="mt-0.5 truncate">{post.source_key}</div>
                </div>
              ) : null}
            </div>
          </CollapsibleContent>

          <Separator />

          <div className="flex flex-wrap items-center justify-between gap-3">
            <CollapsibleTrigger
              className={cn(
                buttonVariants({ variant: "outline", size: "sm" }),
                "h-9 rounded-full px-4 text-muted-foreground hover:text-foreground",
              )}
            >
              <ChevronDown
                className={cn("size-4 transition-transform", open && "rotate-180")}
              />
              {open ? "Свернуть" : "Подробнее"}
            </CollapsibleTrigger>

            {post.post_url ? (
              <a
                className={cn(
                  buttonVariants({ variant: "outline", size: "sm" }),
                  "h-9 rounded-full px-4",
                )}
                href={post.post_url}
                target="_blank"
                rel="noreferrer"
              >
                Открыть в LinkedIn
                <ExternalLink className="size-3.5" />
              </a>
            ) : null}
          </div>
        </CardContent>
      </Collapsible>
    </Card>
  );
}
