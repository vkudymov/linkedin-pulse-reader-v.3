"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { useRouter } from "@/i18n/navigation";

const fieldClassName =
  "h-11 rounded-full border-border/80 bg-secondary px-4 text-sm text-foreground shadow-none";

export default function ResetPasswordPage() {
  const t = useTranslations("auth.reset");
  // Keep locale in deps (router is locale-aware; paths passed without locale prefix).
  const locale = useLocale();
  const router = useRouter();

  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const supabase = createSupabaseBrowserClient();
      const { data } = await supabase.auth.getSession();
      if (!cancelled && !data.session) {
        router.replace("/forgot-password");
        router.refresh();
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [locale, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    setInfo(null);

    const p1 = newPassword.trim();
    const p2 = confirm.trim();
    if (p1.length < 6) {
      setPending(false);
      setError(t("errors.tooShort"));
      return;
    }
    if (p1 !== p2) {
      setPending(false);
      setError(t("errors.mismatch"));
      return;
    }

    try {
      const supabase = createSupabaseBrowserClient();
      const { error } = await supabase.auth.updateUser({ password: p1 });
      if (error) throw error;
      setInfo(t("success"));
      router.replace("/posts");
      router.refresh();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : t("errors.failed");
      setError(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-md rounded-2xl border border-border bg-card py-6 shadow-none ring-0">
        <CardHeader className="gap-1.5 px-6">
          <CardTitle className="text-xl font-semibold tracking-tight">{t("title")}</CardTitle>
          <CardDescription className="text-sm leading-6">{t("description")}</CardDescription>
        </CardHeader>

        <CardContent className="px-6">
          <form className="space-y-5" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="new_password">{t("newPassword")}</Label>
              <Input
                id="new_password"
                className={fieldClassName}
                type="password"
                autoComplete="new-password"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={6}
                disabled={pending}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm_password">{t("confirmPassword")}</Label>
              <Input
                id="confirm_password"
                className={fieldClassName}
                type="password"
                autoComplete="new-password"
                placeholder="••••••••"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                minLength={6}
                disabled={pending}
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
              className="h-11 w-full rounded-full border-0 bg-gradient-to-b from-neutral-200 to-neutral-400 text-neutral-900 shadow-none hover:from-neutral-100 hover:to-neutral-300 disabled:opacity-60"
            >
              <Lock className="size-4" />
              {pending ? t("pending") : t("submit")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

