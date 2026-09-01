"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, MessageSquareText, Newspaper, Save, Shield, UserX } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PostSearchRunner } from "@/components/PostSearchRunner";
import { PromptForm } from "@/components/PromptForm";
import { AdminUserPostsSection } from "@/components/admin/AdminUserPostsSection";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type AdminUserRow = {
  id: string;
  email: string | null;
  created_at: string | null;
  full_name: string | null;
  is_admin: boolean;
  is_blocked: boolean;
  blocked_at: string | null;
  post_search_run_count: number;
};

type UserProfileDetails = {
  id: string;
  full_name: string | null;
  phone: string | null;
  avatar_url: string | null;
  company: string | null;
  job_title: string | null;
  date_of_birth: string | null;
  city: string | null;
  bio: string | null;
  website: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type UserPromptsDetails = {
  id: string;
  search_prompt: string | null;
  comment_prompt: string | null;
  created_at: string | null;
  updated_at: string | null;
};

const fieldClassName =
  "h-11 rounded-full border-border/80 bg-secondary px-4 text-sm text-foreground shadow-none";

function initialsFromName(name: string | null | undefined) {
  const raw = (name || "").trim();
  if (!raw) return "?";
  const parts = raw.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

async function postJson(path: string) {
  const resp = await fetch(path, { method: "POST" });
  const text = await resp.text();
  if (!resp.ok) {
    throw new Error(text || "request failed");
  }
  return text;
}

export function AdminUsersTable({ initialUsers }: { initialUsers: AdminUserRow[] }) {
  const router = useRouter();
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openDetailsById, setOpenDetailsById] = useState<Record<string, boolean>>({});
  const [openPromptsById, setOpenPromptsById] = useState<Record<string, boolean>>({});
  const [openPostsById, setOpenPostsById] = useState<Record<string, boolean>>({});
  const [detailsById, setDetailsById] = useState<Record<string, UserProfileDetails | null>>({});
  const [detailsErrorById, setDetailsErrorById] = useState<Record<string, string | null>>({});
  const [savePendingById, setSavePendingById] = useState<Record<string, boolean>>({});
  const [saveErrorById, setSaveErrorById] = useState<Record<string, string | null>>({});
  const [saveSuccessById, setSaveSuccessById] = useState<Record<string, string | null>>({});
  const [promptsById, setPromptsById] = useState<Record<string, UserPromptsDetails | null>>({});
  const [promptsErrorById, setPromptsErrorById] = useState<Record<string, string | null>>({});
  const [savePromptsErrorById, setSavePromptsErrorById] = useState<Record<string, string | null>>(
    {},
  );
  const [savePromptsSuccessById, setSavePromptsSuccessById] = useState<
    Record<string, string | null>
  >({});

  const users = useMemo(() => initialUsers || [], [initialUsers]);

  async function ensureDetails(userId: string) {
    if (detailsById[userId] !== undefined) return;
    setDetailsErrorById((m) => ({ ...m, [userId]: null }));
    try {
      const resp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/profile`, {
        method: "GET",
      });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || "Не удалось загрузить профиль.");
      }
      const json = (await resp.json()) as UserProfileDetails;
      setDetailsById((m) => ({ ...m, [userId]: json }));
    } catch (e: unknown) {
      setDetailsById((m) => ({ ...m, [userId]: null }));
      setDetailsErrorById((m) => ({
        ...m,
        [userId]: e instanceof Error ? e.message : "Не удалось загрузить профиль.",
      }));
    }
  }

  async function ensurePrompts(userId: string) {
    if (promptsById[userId] !== undefined) return;
    setPromptsErrorById((m) => ({ ...m, [userId]: null }));
    try {
      const resp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/prompts`, {
        method: "GET",
      });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || "Не удалось загрузить промпты.");
      }
      const json = (await resp.json()) as UserPromptsDetails;
      setPromptsById((m) => ({ ...m, [userId]: json }));
    } catch (e: unknown) {
      setPromptsById((m) => ({ ...m, [userId]: null }));
      setPromptsErrorById((m) => ({
        ...m,
        [userId]: e instanceof Error ? e.message : "Не удалось загрузить промпты.",
      }));
    }
  }

  async function refreshPrompts(userId: string) {
    setPromptsErrorById((m) => ({ ...m, [userId]: null }));
    try {
      const resp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/prompts`, {
        method: "GET",
        cache: "no-store",
      });
      if (!resp.ok) {
        const text = await resp.text().catch(() => "");
        throw new Error(text || "Не удалось загрузить промпты.");
      }
      const json = (await resp.json()) as UserPromptsDetails;
      setPromptsById((m) => ({ ...m, [userId]: json }));
    } catch (e: unknown) {
      setPromptsById((m) => ({ ...m, [userId]: null }));
      setPromptsErrorById((m) => ({
        ...m,
        [userId]: e instanceof Error ? e.message : "Не удалось загрузить промпты.",
      }));
    }
  }

  async function onSaveDetails(userId: string) {
    const details = detailsById[userId];
    if (!details) return;
    setSavePendingById((m) => ({ ...m, [userId]: true }));
    setSaveErrorById((m) => ({ ...m, [userId]: null }));
    setSaveSuccessById((m) => ({ ...m, [userId]: null }));
    try {
      const payload = {
        full_name: details.full_name || null,
        phone: details.phone || null,
        avatar_url: details.avatar_url || null,
        company: details.company || null,
        job_title: details.job_title || null,
        date_of_birth: details.date_of_birth || null,
        city: details.city || null,
        bio: details.bio || null,
        website: details.website || null,
      };
      const resp = await fetch(`/api/admin/users/${encodeURIComponent(userId)}/profile`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const text = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(text || "Не удалось сохранить профиль.");
      setSaveSuccessById((m) => ({ ...m, [userId]: "Сохранено." }));
      router.refresh();
    } catch (e: unknown) {
      setSaveErrorById((m) => ({
        ...m,
        [userId]: e instanceof Error ? e.message : "Не удалось сохранить профиль.",
      }));
    } finally {
      setSavePendingById((m) => ({ ...m, [userId]: false }));
    }
  }

  async function onBlock(userId: string) {
    setPendingId(userId);
    setError(null);
    try {
      await postJson(`/api/admin/users/${encodeURIComponent(userId)}/block`);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка запроса");
    } finally {
      setPendingId(null);
    }
  }

  async function onUnblock(userId: string) {
    setPendingId(userId);
    setError(null);
    try {
      await postJson(`/api/admin/users/${encodeURIComponent(userId)}/unblock`);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка запроса");
    } finally {
      setPendingId(null);
    }
  }

  async function onResetCount(userId: string) {
    setPendingId(userId);
    setError(null);
    try {
      await postJson(`/api/admin/users/${encodeURIComponent(userId)}/reset-post-search-count`);
      router.refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка запроса");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <Card className="overflow-hidden rounded-2xl border border-border bg-card">
      <CardHeader className="border-b border-border px-6 py-5">
        <CardTitle className="text-lg font-semibold tracking-tight">Пользователи</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 p-6">
        {error ? (
          <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        <div className="space-y-3">
          {users.map((u) => {
            const pending = pendingId === u.id;
            const openDetails = Boolean(openDetailsById[u.id]);
            const openPrompts = Boolean(openPromptsById[u.id]);
            const openPosts = Boolean(openPostsById[u.id]);
            const email = u.email || "";
            const statusLabel = u.is_blocked ? "Заблокирован" : "Активен";
            const displayName = u.full_name || "—";
            const details = detailsById[u.id];
            const prompts = promptsById[u.id] ?? null;
            const avatarAlt = (displayName || email || "Профиль").trim();
            const avatarFallback = initialsFromName(displayName || email);

            return (
              <Card key={u.id} className="overflow-hidden rounded-2xl border border-border bg-background/40">
                <CardHeader className="gap-2 px-6 pb-4 pt-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="min-w-0 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          {u.is_admin ? <Shield className="size-4 text-foreground/70" aria-hidden /> : null}
                          <div className="truncate text-base font-semibold tracking-tight">{displayName}</div>
                          <div className="truncate text-sm text-muted-foreground">{email}</div>
                          {u.is_admin ? (
                            <Badge variant="secondary" className="rounded-full">
                              admin
                            </Badge>
                          ) : null}
                        </div>
                      </div>

                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs",
                          u.is_blocked
                            ? "border-destructive/30 bg-destructive/10 text-destructive"
                            : "border-emerald-300/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
                        )}
                      >
                        {u.is_blocked ? <UserX className="size-3.5" aria-hidden /> : null}
                        {statusLabel}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                      <div className="text-sm text-muted-foreground">
                        Запуски поиска:{" "}
                        <span className="font-medium text-foreground">{u.post_search_run_count ?? 0}</span>
                      </div>

                      <div className="flex flex-wrap items-center justify-end gap-2">
                        <button
                          type="button"
                          className={cn(
                            buttonVariants({ variant: "outline", size: "sm" }),
                            "h-9 rounded-full px-4 text-muted-foreground hover:text-foreground",
                          )}
                          onClick={() => {
                            const next = !openDetails;
                            setOpenDetailsById((m) => ({ ...m, [u.id]: next }));
                            if (next) void ensureDetails(u.id);
                          }}
                        >
                          {openDetails ? "Свернуть" : "Профиль"}
                          <ChevronDown
                            className={cn(
                              "ml-1 size-4 transition-transform",
                              openDetails && "rotate-180",
                            )}
                            aria-hidden
                          />
                        </button>

                        <button
                          type="button"
                          className={cn(
                            buttonVariants({ variant: "outline", size: "sm" }),
                            "h-9 rounded-full px-4 text-muted-foreground hover:text-foreground",
                          )}
                          onClick={() => {
                            const next = !openPrompts;
                            setOpenPromptsById((m) => ({ ...m, [u.id]: next }));
                            if (next) void ensurePrompts(u.id);
                          }}
                        >
                          <MessageSquareText className="size-4" aria-hidden />
                          {openPrompts ? "Свернуть" : "Промпт"}
                          <ChevronDown
                            className={cn(
                              "ml-1 size-4 transition-transform",
                              openPrompts && "rotate-180",
                            )}
                            aria-hidden
                          />
                        </button>

                        <button
                          type="button"
                          className={cn(
                            buttonVariants({ variant: "outline", size: "sm" }),
                            "h-9 rounded-full px-4 text-muted-foreground hover:text-foreground",
                          )}
                          onClick={() => {
                            const next = !openPosts;
                            setOpenPostsById((m) => ({ ...m, [u.id]: next }));
                          }}
                        >
                          <Newspaper className="size-4" aria-hidden />
                          {openPosts ? "Свернуть" : "Посты"}
                          <ChevronDown
                            className={cn(
                              "ml-1 size-4 transition-transform",
                              openPosts && "rotate-180",
                            )}
                            aria-hidden
                          />
                        </button>

                        {u.is_blocked ? (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={pending}
                            className="h-9 rounded-full px-4"
                            onClick={() => onUnblock(u.id)}
                          >
                            Разблокировать
                          </Button>
                        ) : (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={pending}
                            className="h-9 rounded-full px-4 text-destructive hover:text-destructive"
                            onClick={() => onBlock(u.id)}
                          >
                            Заблокировать
                          </Button>
                        )}

                        <Button
                          variant="outline"
                          size="sm"
                          disabled={pending}
                          className="h-9 rounded-full px-4"
                          onClick={() => onResetCount(u.id)}
                        >
                          Обнулить счётчик
                        </Button>
                      </div>
                    </div>
                  </CardHeader>

                  {openDetails ? (
                    <CardContent className="space-y-3 px-6 pb-6 pt-0">
                      {saveErrorById[u.id] ? (
                        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                          {saveErrorById[u.id]}
                        </div>
                      ) : null}
                      {saveSuccessById[u.id] ? (
                        <div className="rounded-xl border border-emerald-300/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
                          {saveSuccessById[u.id]}
                        </div>
                      ) : null}

                      {detailsErrorById[u.id] ? (
                        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                          {detailsErrorById[u.id]}
                        </div>
                      ) : null}

                      {detailsById[u.id] ? (
                        <form
                          className="space-y-6 rounded-xl border border-border bg-background/60 p-4"
                          onSubmit={(e) => {
                            e.preventDefault();
                            void onSaveDetails(u.id);
                          }}
                        >
                          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                            <div className="flex items-center gap-4">
                              <Avatar size="default" className="size-14">
                                {details?.avatar_url ? (
                                  <AvatarImage src={details.avatar_url} alt={avatarAlt} />
                                ) : null}
                                <AvatarFallback className="bg-background text-base font-medium text-foreground">
                                  {avatarFallback}
                                </AvatarFallback>
                              </Avatar>

                              <div className="min-w-0">
                                <div className="text-sm font-medium text-foreground">Профиль</div>
                                <div className="text-sm text-muted-foreground">
                                  Администратор может редактировать данные пользователя.
                                </div>
                              </div>
                            </div>
                          </div>

                          <div className="grid gap-5 sm:grid-cols-2">
                            <div className="space-y-2">
                              <Label htmlFor={`phone_${u.id}`}>Телефон</Label>
                              <Input
                                id={`phone_${u.id}`}
                                className={fieldClassName}
                                autoComplete="tel"
                                value={details?.phone || ""}
                                onChange={(e) =>
                                  setDetailsById((m) => ({
                                    ...m,
                                    [u.id]: { ...(m[u.id] as UserProfileDetails), phone: e.target.value },
                                  }))
                                }
                                disabled={Boolean(savePendingById[u.id])}
                                placeholder="+7 999 000-00-00"
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor={`company_${u.id}`}>Компания</Label>
                              <Input
                                id={`company_${u.id}`}
                                className={fieldClassName}
                                value={details?.company || ""}
                                onChange={(e) =>
                                  setDetailsById((m) => ({
                                    ...m,
                                    [u.id]: { ...(m[u.id] as UserProfileDetails), company: e.target.value },
                                  }))
                                }
                                disabled={Boolean(savePendingById[u.id])}
                                placeholder="Название компании"
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor={`job_title_${u.id}`}>Должность</Label>
                              <Input
                                id={`job_title_${u.id}`}
                                className={fieldClassName}
                                value={details?.job_title || ""}
                                onChange={(e) =>
                                  setDetailsById((m) => ({
                                    ...m,
                                    [u.id]: { ...(m[u.id] as UserProfileDetails), job_title: e.target.value },
                                  }))
                                }
                                disabled={Boolean(savePendingById[u.id])}
                                placeholder="Должность"
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor={`date_of_birth_${u.id}`}>Дата рождения</Label>
                              <Input
                                id={`date_of_birth_${u.id}`}
                                className={fieldClassName}
                                type="date"
                                value={details?.date_of_birth || ""}
                                onChange={(e) =>
                                  setDetailsById((m) => ({
                                    ...m,
                                    [u.id]: {
                                      ...(m[u.id] as UserProfileDetails),
                                      date_of_birth: e.target.value,
                                    },
                                  }))
                                }
                                disabled={Boolean(savePendingById[u.id])}
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor={`city_${u.id}`}>Город</Label>
                              <Input
                                id={`city_${u.id}`}
                                className={fieldClassName}
                                value={details?.city || ""}
                                onChange={(e) =>
                                  setDetailsById((m) => ({
                                    ...m,
                                    [u.id]: { ...(m[u.id] as UserProfileDetails), city: e.target.value },
                                  }))
                                }
                                disabled={Boolean(savePendingById[u.id])}
                                placeholder="Город"
                              />
                            </div>

                            <div className="space-y-2">
                              <Label htmlFor={`website_${u.id}`}>Сайт</Label>
                              <Input
                                id={`website_${u.id}`}
                                className={fieldClassName}
                                value={details?.website || ""}
                                onChange={(e) =>
                                  setDetailsById((m) => ({
                                    ...m,
                                    [u.id]: { ...(m[u.id] as UserProfileDetails), website: e.target.value },
                                  }))
                                }
                                disabled={Boolean(savePendingById[u.id])}
                                placeholder="https://example.com"
                              />
                            </div>
                          </div>

                          <div className="space-y-2">
                            <Label htmlFor={`bio_${u.id}`}>О себе</Label>
                            <Textarea
                              id={`bio_${u.id}`}
                              value={details?.bio || ""}
                              onChange={(e) =>
                                setDetailsById((m) => ({
                                  ...m,
                                  [u.id]: { ...(m[u.id] as UserProfileDetails), bio: e.target.value },
                                }))
                              }
                              disabled={Boolean(savePendingById[u.id])}
                              placeholder="Несколько строк о пользователе"
                              className={cn(
                                "min-h-28 resize-y rounded-xl border-border/80 bg-secondary px-4 py-3 text-sm text-foreground shadow-none",
                              )}
                            />
                          </div>

                          <Button
                            type="submit"
                            className="h-11 w-full rounded-full bg-gradient-to-b from-neutral-200 to-neutral-400 text-sm font-semibold text-neutral-900 shadow-none hover:from-neutral-100 hover:to-neutral-300"
                            disabled={Boolean(savePendingById[u.id])}
                          >
                            <Save className="mr-2 size-4" />
                            {savePendingById[u.id] ? "Сохраняем..." : "Сохранить"}
                          </Button>
                        </form>
                      ) : (
                        <div className="text-sm text-muted-foreground">Загружаем профиль…</div>
                      )}
                    </CardContent>
                  ) : null}

                  {openPrompts ? (
                    <CardContent className="space-y-3 border-t border-border px-6 pb-6 pt-6">
                      {promptsErrorById[u.id] ? (
                        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                          {promptsErrorById[u.id]}
                        </div>
                      ) : null}
                      {savePromptsErrorById[u.id] ? (
                        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                          {savePromptsErrorById[u.id]}
                        </div>
                      ) : null}
                      {savePromptsSuccessById[u.id] ? (
                        <div className="rounded-xl border border-emerald-300/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
                          {savePromptsSuccessById[u.id]}
                        </div>
                      ) : null}

                      {prompts ? (
                        <div className="space-y-6 rounded-xl border border-border bg-background/60 p-4">
                          <PromptForm
                            initialProfile={null}
                            initialSearchPrompt={prompts.search_prompt}
                            initialCommentPrompt={prompts.comment_prompt}
                            saveUrl={`/api/admin/users/${encodeURIComponent(u.id)}/prompts`}
                            fieldIdPrefix={`prompts_${u.id}`}
                            footerHint="Сохранение происходит для выбранного пользователя."
                            onSaved={() => {
                              setSavePromptsErrorById((m) => ({ ...m, [u.id]: null }));
                              setSavePromptsSuccessById((m) => ({ ...m, [u.id]: "Сохранено." }));
                              void refreshPrompts(u.id);
                            }}
                          />

                          <div className="border-t border-border/80 pt-6">
                            <PostSearchRunner
                              runUrl={`/api/admin/users/${encodeURIComponent(u.id)}/post-search/run`}
                              statusUrl={(sid) =>
                                `/api/admin/users/${encodeURIComponent(u.id)}/post-search/run/${encodeURIComponent(sid)}`
                              }
                              redirectOnSuccess={false}
                              successMessage="Поиск постов завершён."
                              onSuccess={() => {
                                void refreshPrompts(u.id);
                                router.refresh();
                              }}
                            />
                          </div>
                        </div>
                      ) : (
                        <div className="text-sm text-muted-foreground">Загружаем промпты…</div>
                      )}
                    </CardContent>
                  ) : null}

                  {openPosts ? (
                    <CardContent className="space-y-3 border-t border-border px-6 pb-6 pt-6">
                      <AdminUserPostsSection userId={u.id} />
                    </CardContent>
                  ) : null}
              </Card>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

