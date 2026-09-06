"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { Link } from "@/i18n/navigation";

const fieldClassName =
  "h-11 rounded-full border-border/80 bg-secondary px-4 text-sm text-foreground shadow-none";

export default function ForgotPasswordPage() {
  const t = useTranslations("auth.forgot");
  const locale = useLocale();

  const [email, setEmail] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    setInfo(null);

    try {
      const origin = window.location.origin;
      const redirectTo = `${origin}/auth/callback?next=/${locale}/reset-password`;

      const supabase = createSupabaseBrowserClient();
      const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo });
      if (error) throw error;

      setInfo(t("success"));
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
              <Mail className="size-4" />
              {pending ? t("pending") : t("submit")}
            </Button>

            <div className="text-center text-sm text-muted-foreground">
              <Link
                className="underline-offset-4 hover:text-foreground hover:underline"
                href="/login"
              >
                {t("backToLogin")}
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

