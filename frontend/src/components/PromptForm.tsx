"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Save, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";

import {
  COMMENT_REQUIRED_MARKERS,
  DEFAULT_COMMENT_PROMPT,
  DEFAULT_SEARCH_PROMPT,
  SEARCH_REQUIRED_MARKER,
} from "@/lib/defaultPrompts";
import { cn } from "@/lib/utils";
import type { UserProfileRow } from "@/types/database";
import { getPromptIssues, validatePromptPayload } from "@/lib/validatePrompts";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function PromptForm({
  initialProfile,
  initialSearchPrompt,
  initialCommentPrompt,
  saveUrl = "/api/account/prompts",
  fieldIdPrefix,
  footerHint,
  onSaved,
}: {
  initialProfile: UserProfileRow | null;
  initialSearchPrompt?: string | null;
  initialCommentPrompt?: string | null;
  saveUrl?: string;
  fieldIdPrefix?: string;
  footerHint?: string;
  onSaved?: () => void;
}) {
  const t = useTranslations("promptsForm");

  const footerHintText = footerHint ?? t("footerHintDefault");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const initialSearch = initialSearchPrompt ?? initialProfile?.search_prompt ?? "";
  const initialComment = initialCommentPrompt ?? initialProfile?.comment_prompt ?? "";
  const [searchPrompt, setSearchPrompt] = useState(initialSearch);
  const [commentPrompt, setCommentPrompt] = useState(initialComment);
  const lastInitialRef = useRef({ initialSearch, initialComment });

  useEffect(() => {
    // Update form when upstream value changes, but don't clobber user edits.
    if (pending) return;
    const prev = lastInitialRef.current;
    const canUpdateSearch = searchPrompt === prev.initialSearch;
    const canUpdateComment = commentPrompt === prev.initialComment;
    if (canUpdateSearch) setSearchPrompt(initialSearch);
    if (canUpdateComment) setCommentPrompt(initialComment);
    lastInitialRef.current = { initialSearch, initialComment };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialSearch, initialComment, pending]);

  const issues = useMemo(
    () => getPromptIssues({ search_prompt: searchPrompt, comment_prompt: commentPrompt }),
    [commentPrompt, searchPrompt],
  );
  const isInvalid =
    issues.isSearchEmpty ||
    issues.searchMissing.length > 0 ||
    (commentPrompt.trim().length > 0 && issues.commentMissing.length > 0);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    setSuccess(null);

    const trimmedSearch = searchPrompt.trim();
    const trimmedComment = commentPrompt.trim();

    try {
      const validated = validatePromptPayload({
        search_prompt: trimmedSearch,
        comment_prompt: trimmedComment,
      });
      if (!validated.ok) {
        const err = validated.error;
        if (err.code === "search_required") {
          throw new Error(t("errors.searchRequired"));
        }
        if (err.code === "search_missing_marker") {
          throw new Error(t("errors.searchMissingMarker", { marker: err.marker }));
        }
        if (err.code === "comment_missing_markers") {
          throw new Error(
            t("errors.commentMissingMarkers", { markers: err.missing.join(", ") }),
          );
        }
        throw new Error(t("errors.invalid"));
      }
      const res = await fetch(saveUrl, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(validated.value),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { error?: string } | null;
        const message = data?.error || t("errors.saveFailed");
        throw new Error(message);
      }

      setSuccess(t("success.saved"));
      onSaved?.();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : t("errors.saveFailed");
      setError(message);
      void fetch("/api/log", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          level: "error",
          scope: "prompts.save",
          message,
          where: "src/components/PromptForm.tsx",
        }),
      }).catch(() => { });
    } finally {
      setPending(false);
    }
  }

  const idPrefix = fieldIdPrefix ? `${fieldIdPrefix}_` : "";
  const searchId = `${idPrefix}search_prompt`;
  const commentId = `${idPrefix}comment_prompt`;

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="space-y-2">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <Label htmlFor={searchId} className="text-sm font-medium">
            {t("search.title")}
          </Label>

          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={pending}
            onClick={() => setSearchPrompt(DEFAULT_SEARCH_PROMPT)}
            className="self-start sm:self-auto"
          >
            <Sparkles className="mr-2 h-4 w-4" />
            {t("actions.insertTemplate")}
          </Button>
        </div>

        <Textarea
          id={searchId}
          value={searchPrompt}
          onChange={(e) => setSearchPrompt(e.target.value)}
          disabled={pending}
          className="min-h-56 font-mono text-xs leading-5 md:text-sm"
          placeholder={t("search.placeholder", { marker: SEARCH_REQUIRED_MARKER })}
        />

        <div className="space-y-1 text-xs leading-5 text-muted-foreground">
          <p>
            {t("search.helpMarker.before")} <code>{SEARCH_REQUIRED_MARKER}</code>{" "}
            {t("search.helpMarker.after")}
          </p>
          <p>
            {t("search.helpJson.before")} <code>relevant</code>, <code>score</code>,{" "}
            <code>content_type</code>, <code>main_topics</code>, <code>reason</code>,{" "}
            <code>selection_reason</code>.
          </p>
          {issues.isSearchEmpty ? (
            <p className="text-destructive">{t("search.emptyWarning")}</p>
          ) : null}
          {issues.searchMissing.length > 0 ? (
            <p className="text-destructive">
              {t("search.missingMarker", { markers: issues.searchMissing.join(", ") })}
            </p>
          ) : null}
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <Label htmlFor={commentId} className="text-sm font-medium">
            {t("comment.title")}
          </Label>

          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={pending}
            onClick={() => setCommentPrompt(DEFAULT_COMMENT_PROMPT)}
            className="self-start sm:self-auto"
          >
            <Sparkles className="mr-2 h-4 w-4" />
            {t("actions.insertTemplate")}
          </Button>
        </div>

        <Textarea
          id={commentId}
          value={commentPrompt}
          onChange={(e) => setCommentPrompt(e.target.value)}
          disabled={pending}
          className="min-h-56 font-mono text-xs leading-5 md:text-sm"
          placeholder={t("comment.placeholder")}
        />

        <div className="space-y-1 text-xs leading-5 text-muted-foreground">
          <p>
            {t("comment.helpMarkers.before")} <code>{"<<<...>>>"}</code>{" "}
            {t("comment.helpMarkers.after")}
          </p>
          <p>
            {t("comment.helpRequiredMarkers")}{" "}
            {COMMENT_REQUIRED_MARKERS.map((m) => (
              <code key={m} className="mr-2">
                {m}
              </code>
            ))}
          </p>
          <p>
            {t("comment.helpSubstitutions.before")} <code>{"<<<POST_TEXT>>>"}</code>{" "}
            {t("comment.helpSubstitutions.postText")} <code>{"<<<CONTENT_TYPE>>>"}</code>{" "}
            {t("comment.helpSubstitutions.contentType")} <code>{"<<<MAIN_TOPICS>>>"}</code>{" "}
            {t("comment.helpSubstitutions.mainTopics")} <code>{"<<<TARGET_LANGUAGE>>>"}</code>{" "}
            {t("comment.helpSubstitutions.targetLanguage")}
          </p>
          {commentPrompt.trim() && issues.commentMissing.length > 0 ? (
            <p className="text-destructive">
              {t("comment.missingMarkers", { markers: issues.commentMissing.join(", ") })}
            </p>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {success ? (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-600 dark:text-emerald-300">
          {success}
        </div>
      ) : null}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className={cn("text-xs text-muted-foreground", isInvalid ? "text-destructive" : "")}>
          {isInvalid
            ? t("footer.invalid")
            : footerHintText}
        </p>

        <Button type="submit" disabled={pending || isInvalid} className="rounded-full">
          <Save className="mr-2 h-4 w-4" />
          {pending ? t("actions.saving") : t("actions.save")}
        </Button>
      </div>
    </form>
  );
}

