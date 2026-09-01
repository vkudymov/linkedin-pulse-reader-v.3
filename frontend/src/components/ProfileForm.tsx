"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Lock, Save } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { UserProfileRow } from "@/types/database";

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

export function ProfileForm({
  userId,
  email,
  initialProfile,
}: {
  userId: string;
  email: string;
  initialProfile: UserProfileRow | null;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [fullName, setFullName] = useState(initialProfile?.full_name ?? "");
  const [phone, setPhone] = useState(initialProfile?.phone ?? "");
  const [company, setCompany] = useState(initialProfile?.company ?? "");
  const [jobTitle, setJobTitle] = useState(initialProfile?.job_title ?? "");
  const [dateOfBirth, setDateOfBirth] = useState(initialProfile?.date_of_birth ?? "");
  const [city, setCity] = useState(initialProfile?.city ?? "");
  const [website, setWebsite] = useState(initialProfile?.website ?? "");
  const [bio, setBio] = useState(initialProfile?.bio ?? "");
  const [avatarUrl, setAvatarUrl] = useState(initialProfile?.avatar_url ?? "");
  const [avatarImgSrc, setAvatarImgSrc] = useState<string>(initialProfile?.avatar_url ?? "");
  const avatarPreviewUrlRef = useRef<string | null>(null);

  const avatarAlt = useMemo(() => (fullName || email || "Профиль").trim(), [email, fullName]);
  const avatarFallback = useMemo(() => initialsFromName(fullName || email), [email, fullName]);

  useEffect(() => {
    // Reset displayed src to the canonical URL (async to satisfy hooks lint rules).
    queueMicrotask(() => setAvatarImgSrc(avatarUrl ? `${avatarUrl}?v=${Date.now()}` : ""));

    if (!avatarUrl) return;

    // Browser <img> loads can fail with QUIC/range (206). Use a blob URL as a fallback.
    let cancelled = false;
    let objectUrl: string | null = null;

    (async () => {
      try {
        const r = await fetch(`${avatarUrl}?v=${Date.now()}`, { method: "GET", cache: "no-store" });
        if (!r.ok) return;
        const blob = await r.blob();
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setAvatarImgSrc(objectUrl);
        if (avatarPreviewUrlRef.current) {
          URL.revokeObjectURL(avatarPreviewUrlRef.current);
          avatarPreviewUrlRef.current = null;
        }
      } catch {
        // Swallow: we'll fallback to AvatarFallback.
      }
    })();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [avatarUrl]);

  async function onUploadAvatar(file: File) {
    // Workaround for browser-to-Supabase storage timeouts: upload via same-origin API.
    const fd = new FormData();
    fd.set("file", file);
    const resp = await fetch("/api/account/avatar", { method: "POST", body: fd });
    type ApiResponse = { ok: true; publicUrl: string } | { ok: false; error?: string };
    const json = (await resp.json().catch(() => null)) as ApiResponse | null;
    const publicUrl = json && json.ok === true ? json.publicUrl : null;
    if (!resp.ok || !publicUrl) {
      throw new Error((json && "error" in json && typeof json.error === "string" && json.error) || "Не удалось загрузить аватар.");
    }
    return publicUrl;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    setSuccess(null);

    try {
      const payload = {
        full_name: fullName.trim() || null,
        phone: phone.trim() || null,
        avatar_url: avatarUrl.trim() || null,
        company: company.trim() || null,
        job_title: jobTitle.trim() || null,
        date_of_birth: dateOfBirth || null,
        city: city.trim() || null,
        website: website.trim() || null,
        bio: bio.trim() || null,
      };

      const res = await fetch("/api/account/profile", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as { error?: string } | null;
        const message = data?.error || "Не удалось сохранить профиль.";
        throw new Error(message);
      }
      setSuccess("Профиль сохранён.");
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Не удалось сохранить профиль.";
      setError(message);
      void fetch("/api/log", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          level: "error",
          scope: "profile.save",
          message,
          where: "src/components/ProfileForm.tsx",
        }),
      }).catch(() => { });
    } finally {
      setPending(false);
    }
  }

  async function onPickAvatar(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPending(true);
    setError(null);
    setSuccess(null);

    try {
      // Show immediate local preview (works for all users).
      if (avatarPreviewUrlRef.current) URL.revokeObjectURL(avatarPreviewUrlRef.current);
      avatarPreviewUrlRef.current = URL.createObjectURL(file);
      setAvatarImgSrc(avatarPreviewUrlRef.current);

      const publicUrl = await onUploadAvatar(file);
      setAvatarUrl(publicUrl);
      void userId;
      setSuccess("Аватар загружен. Нажмите «Сохранить», чтобы закрепить его в профиле.");
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Не удалось загрузить аватар.";
      setError(message);
    } finally {
      setPending(false);
      e.target.value = "";
    }
  }

  return (
    <form className="space-y-6" onSubmit={onSubmit}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Avatar size="default" className="size-14">
            {avatarImgSrc ? (
              <AvatarImage
                key={avatarImgSrc}
                src={avatarImgSrc}
                alt={avatarAlt}
              />
            ) : null}
            <AvatarFallback className="bg-background text-base font-medium text-foreground">
              {avatarFallback}
            </AvatarFallback>
          </Avatar>

          <div className="min-w-0">
            <div className="text-sm font-medium text-foreground">Аватар</div>
            <div className="text-sm text-muted-foreground">
              PNG, JPG или WebP, до 2MB.
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Label
            className={cn(
              "inline-flex h-9 cursor-pointer items-center rounded-full border border-border bg-secondary px-4 text-sm text-muted-foreground hover:text-foreground",
              pending && "pointer-events-none opacity-60",
            )}
          >
            Выбрать файл
            <input
              className="sr-only"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={onPickAvatar}
              disabled={pending}
            />
          </Label>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {success ? (
        <div className="rounded-xl border border-border/80 bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
          {success}
        </div>
      ) : null}

      <div className="grid gap-5 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <div className="relative">
            <Input
              id="email"
              className={cn(fieldClassName, "pr-10 text-muted-foreground")}
              value={email}
              disabled
              readOnly
            />
            <Lock className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground/70" />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="full_name">Имя</Label>
          <Input
            id="full_name"
            className={fieldClassName}
            autoComplete="name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            disabled={pending}
            placeholder="Иван Иванов"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="phone">Телефон</Label>
          <Input
            id="phone"
            className={fieldClassName}
            autoComplete="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            disabled={pending}
            placeholder="+7 999 000-00-00"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="company">Компания</Label>
          <Input
            id="company"
            className={fieldClassName}
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            disabled={pending}
            placeholder="Название компании"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="job_title">Должность</Label>
          <Input
            id="job_title"
            className={fieldClassName}
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            disabled={pending}
            placeholder="Должность"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="date_of_birth">Дата рождения</Label>
          <Input
            id="date_of_birth"
            className={fieldClassName}
            type="date"
            value={dateOfBirth}
            onChange={(e) => setDateOfBirth(e.target.value)}
            disabled={pending}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="city">Город</Label>
          <Input
            id="city"
            className={fieldClassName}
            value={city}
            onChange={(e) => setCity(e.target.value)}
            disabled={pending}
            placeholder="Город"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="website">Сайт</Label>
          <Input
            id="website"
            className={fieldClassName}
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
            disabled={pending}
            placeholder="https://example.com"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="bio">О себе</Label>
        <textarea
          id="bio"
          className={cn(
            "min-h-28 w-full resize-y rounded-xl border border-border/80 bg-secondary px-4 py-3 text-sm text-foreground shadow-none outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
            pending && "opacity-60",
          )}
          value={bio}
          onChange={(e) => setBio(e.target.value)}
          disabled={pending}
          placeholder="Несколько строк о вас"
        />
      </div>

      <Button
        type="submit"
        className="h-11 w-full rounded-full bg-gradient-to-b from-neutral-200 to-neutral-400 text-sm font-semibold text-neutral-900 shadow-none hover:from-neutral-100 hover:to-neutral-300"
        disabled={pending}
      >
        <Save className="mr-2 size-4" />
        {pending ? "Сохраняем..." : "Сохранить"}
      </Button>
    </form>
  );
}

