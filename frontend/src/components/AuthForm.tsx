"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Lock } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { Link } from "@/i18n/navigation";

type Variant = "login" | "register";

const fieldClassName =
  "h-11 rounded-full border-border/80 bg-secondary px-4 text-sm text-foreground shadow-none";

export function AuthForm({ variant }: { variant: Variant }) {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("auth");
  const copy = {
    title: t(`${variant}.title`),
    description: t(`${variant}.description`),
    submit: t(`${variant}.submit`),
    pending: t(`${variant}.pending`),
    passwordLabel: t("password"),
    alt:
      variant === "login"
        ? { href: "/register", label: t("login.alt") }
        : { href: "/login", label: t("register.alt") },
  } as const;
  const nextPath = `/${locale}/posts`;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    setInfo(null);

    try {
      const supabase = createSupabaseBrowserClient();
      if (variant === "register") {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        // Best-effort: persist UI locale for the new user (if session exists).
        void fetch("/api/account/locale", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ locale }),
        }).catch(() => {});
        setInfo(t("register.createdInfo"));
        return;
      }

      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;

      const { data: userData } = await supabase.auth.getUser();
      const uid = userData.user?.id ?? null;
      if (uid) {
        const { data: profile } = await supabase
          .from("user_admin_state")
          .select("is_blocked")
          .eq("id", uid)
          .maybeSingle();
        if (profile?.is_blocked) {
          await supabase.auth.signOut();
          setError(t("errors.blockedUser"));
          return;
        }

        // Prefer server-stored locale for redirects after login.
        const { data: pref } = await supabase
          .from("user_profiles")
          .select("locale")
          .eq("id", uid)
          .maybeSingle();
        const storedLocale = pref?.locale === "en" ? "en" : pref?.locale === "ru" ? "ru" : null;
        const target = storedLocale ? `/${storedLocale}/posts` : nextPath;

        // Keep locale cookie in sync (also helps <html lang>).
        void fetch("/api/account/locale", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ locale: storedLocale || locale }),
        }).catch(() => {});

        router.push(target);
        router.refresh();
        return;
      }
      router.push(nextPath);
      router.refresh();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : t("errors.authFailed");
      const scope = variant === "register" ? "auth.register" : "auth.login";
      console.error(`[ERROR] ${scope} ${message}`);
      void fetch("/api/log", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          level: "error",
          scope,
          message,
          where: "src/components/AuthForm.tsx",
        }),
      }).catch(() => {});
      setError(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-md rounded-2xl border border-border bg-card py-6 shadow-none ring-0">
        <CardHeader className="gap-1.5 px-6">
          <CardTitle className="text-xl font-semibold tracking-tight">
            {copy.title}
          </CardTitle>
          <CardDescription className="text-sm leading-6">
            {copy.description}
          </CardDescription>
        </CardHeader>

        <CardContent className="px-6">
          <form className="space-y-5" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                className={fieldClassName}
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between gap-3">
                <Label htmlFor="password">{copy.passwordLabel}</Label>
              </div>
              <Input
                id="password"
                className={fieldClassName}
                type="password"
                autoComplete={
                  variant === "register" ? "new-password" : "current-password"
                }
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>

            {error ? (
              <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            ) : null}

            {info ? (
              <div className="rounded-xl border border-border/80 bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
                {info}
              </div>
            ) : null}

            <Button
              type="submit"
              disabled={pending}
              className={cn(
                "h-11 w-full rounded-full border-0 bg-gradient-to-b from-neutral-200 to-neutral-400",
                "text-neutral-900 shadow-none hover:from-neutral-100 hover:to-neutral-300",
                "disabled:opacity-60",
              )}
            >
              <Lock className="size-4" />
              {pending ? copy.pending : copy.submit}
            </Button>
          </form>
        </CardContent>

        <CardFooter className="justify-center px-6 pt-2">
          <Link
            className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            href={copy.alt.href}
          >
            {copy.alt.label}
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
}
