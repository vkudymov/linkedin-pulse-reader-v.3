"use client";

import { useMemo, useState } from "react";
import { Save, Sparkles } from "lucide-react";

import {
  COMMENT_REQUIRED_MARKERS,
  DEFAULT_COMMENT_PROMPT,
  DEFAULT_SEARCH_PROMPT,
  SEARCH_REQUIRED_MARKER,
} from "@/lib/defaultPrompts";
import { cn } from "@/lib/utils";
import type { UserProfileRow } from "@/types/database";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

function missingMarkers(value: string, markers: readonly string[]) {
  const v = value || "";
  return markers.filter((m) => !v.includes(m));
}

export function PromptForm({
  initialProfile,
}: {
  initialProfile: UserProfileRow | null;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [searchPrompt, setSearchPrompt] = useState(initialProfile?.search_prompt ?? "");
  const [commentPrompt, setCommentPrompt] = useState(initialProfile?.comment_prompt ?? "");

  const searchMissing = useMemo(
    () => missingMarkers(searchPrompt, [SEARCH_REQUIRED_MARKER]),
    [searchPrompt]
  );
  const commentMissing = useMemo(
    () =>
      commentPrompt.trim()
        ? missingMarkers(commentPrompt, [...COMMENT_REQUIRED_MARKERS])
        : ([] as string[]),
    [commentPrompt]
  );

  const isSearchEmpty = !searchPrompt.trim();
  const isInvalid =
    isSearchEmpty || searchMissing.length > 0 || (commentPrompt.trim() && commentMissing.length > 0);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    setSuccess(null);

    const trimmedSearch = searchPrompt.trim();
    const trimmedComment = commentPrompt.trim();

    try {
      if (!trimmedSearch) {
        throw new Error("Промпт поиска обязателен.");
      }
      if (!trimmedSearch.includes(SEARCH_REQUIRED_MARKER)) {
        throw new Error(`Промпт поиска должен содержать маркер ${SEARCH_REQUIRED_MARKER}.`);
      }
      if (trimmedComment) {
        const missing = missingMarkers(trimmedComment, [...COMMENT_REQUIRED_MARKERS]);
        if (missing.length > 0) {
          throw new Error(
            `Промпт комментария должен содержать маркеры: ${missing.join(", ")}.`
          );
        }
      }

      const payload = {
        search_prompt: trimmedSearch,
        comment_prompt: trimmedComment || null,
      };
      const res = await fetch("/api/account/prompts", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { error?: string } | null;
        const message = data?.error || "Не удалось сохранить промпты.";
        throw new Error(message);
      }

      setSuccess("Промпты сохранены.");
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Не удалось сохранить промпты.";
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
      }).catch(() => {});
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="space-y-2">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <Label htmlFor="search_prompt" className="text-sm font-medium">
            Промпт поиска (релевантность)
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
            Вставить шаблон
          </Button>
        </div>

        <Textarea
          id="search_prompt"
          value={searchPrompt}
          onChange={(e) => setSearchPrompt(e.target.value)}
          disabled={pending}
          className="min-h-56 font-mono text-xs leading-5 md:text-sm"
          placeholder={`Должен содержать ${SEARCH_REQUIRED_MARKER} и просить строгий JSON-ответ.`}
        />

        <div className="space-y-1 text-xs leading-5 text-muted-foreground">
          <p>
            Маркер обязателен: <code>{SEARCH_REQUIRED_MARKER}</code>. Ответ модели должен быть JSON с
            полями <code>relevant</code>, <code>score</code>, <code>content_type</code>,{" "}
            <code>main_topics</code>, <code>reason</code>, <code>selection_reason</code>.
          </p>
          {isSearchEmpty ? (
            <p className="text-destructive">Промпт поиска не заполнен — worker не будет анализировать посты.</p>
          ) : null}
          {searchMissing.length > 0 ? (
            <p className="text-destructive">
              Не хватает маркера: {searchMissing.join(", ")}.
            </p>
          ) : null}
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <Label htmlFor="comment_prompt" className="text-sm font-medium">
            Промпт комментария (опционально)
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
            Вставить шаблон
          </Button>
        </div>

        <Textarea
          id="comment_prompt"
          value={commentPrompt}
          onChange={(e) => setCommentPrompt(e.target.value)}
          disabled={pending}
          className="min-h-56 font-mono text-xs leading-5 md:text-sm"
          placeholder="Если оставить пустым, генерация комментариев будет отключена."
        />

        <div className="space-y-1 text-xs leading-5 text-muted-foreground">
          <p>
            Если заполняете, шаблон должен содержать маркеры:{" "}
            {COMMENT_REQUIRED_MARKERS.map((m) => (
              <code key={m} className="mr-2">
                {m}
              </code>
            ))}
          </p>
          {commentPrompt.trim() && commentMissing.length > 0 ? (
            <p className="text-destructive">
              Не хватает маркеров: {commentMissing.join(", ")}.
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
            ? "Исправьте ошибки выше, чтобы сохранить."
            : "Сохранение происходит в таблицу user_profiles (видно только вам)."}
        </p>

        <Button type="submit" disabled={pending || isInvalid} className="rounded-full">
          <Save className="mr-2 h-4 w-4" />
          Сохранить промпты
        </Button>
      </div>
    </form>
  );
}

