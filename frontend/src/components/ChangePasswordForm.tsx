"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Link, useRouter } from "@/i18n/navigation";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

const fieldClassName =
  "h-11 rounded-full border-border/80 bg-secondary px-4 text-sm text-foreground shadow-none";

export function ChangePasswordForm({ email }: { email: string }) {
  const t = useTranslations("account.security");
  const locale = useLocale();
  const router = useRouter();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    setSuccess(null);

    const cur = currentPassword;
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
    if (cur === p1) {
      setPending(false);
      setError(t("errors.sameAsCurrent"));
      return;
    }

    try {
      const supabase = createSupabaseBrowserClient();
      const { error: authError } = await supabase.auth.signInWithPassword({
        email,
        password: cur,
      });
      if (authError) throw authError;

      const { error: updError } = await supabase.auth.updateUser({ password: p1 });
      if (updError) throw updError;

      setCurrentPassword("");
      setNewPassword("");
      setConfirm("");
      setSuccess(t("success"));
      router.refresh();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : t("errors.failed");
      setError(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="space-y-5" onSubmit={onSubmit}>
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <Label htmlFor="current_password">{t("currentPassword")}</Label>
          <Link
            className="text-xs text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            href="/forgot-password"
          >
            {t("forgotLink")}
          </Link>
        </div>
        <Input
          id="current_password"
          className={fieldClassName}
          type="password"
          autoComplete="current-password"
          placeholder="••••••••"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          required
          disabled={pending}
          minLength={6}
        />
      </div>

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
          disabled={pending}
          minLength={6}
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
          disabled={pending}
          minLength={6}
        />
      </div>

      {error ? (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {success ? (
        <div className="rounded-xl border border-emerald-300/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-300">
          {success}
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
  );
}

