"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/client";

type Variant = "login" | "register";

export function AuthForm({ variant }: { variant: Variant }) {
  const router = useRouter();
  const nextPath = "/posts";

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
        setInfo(
          "Пользователь создан. Если включено подтверждение email, проверьте почту и перейдите по ссылке.",
        );
        return;
      }

      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      router.push(nextPath);
      router.refresh();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Ошибка авторизации.";
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

  const title = variant === "register" ? "Регистрация" : "Вход";
  const alt = variant === "register" ? { href: "/login", label: "Уже есть аккаунт? Войти" } : { href: "/register", label: "Нет аккаунта? Зарегистрироваться" };

  return (
    <div className="min-h-[calc(100vh-1px)] flex items-center justify-center p-6">
      <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-semibold">{title}</h1>
        <p className="mt-1 text-sm text-zinc-600">
          LinkedIn Pulse Reader (MVP)
        </p>

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <label className="block">
            <div className="text-sm font-medium text-zinc-800">Email</div>
            <input
              className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 outline-none focus:ring-2 focus:ring-zinc-900/10"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>

          <label className="block">
            <div className="text-sm font-medium text-zinc-800">Пароль</div>
            <input
              className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2 outline-none focus:ring-2 focus:ring-zinc-900/10"
              type="password"
              autoComplete={variant === "register" ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </label>

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              {error}
            </div>
          )}
          {info && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
              {info}
            </div>
          )}

          <button
            type="submit"
            disabled={pending}
            className="w-full rounded-xl bg-zinc-900 px-3 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-60"
          >
            {pending ? "Подождите..." : title}
          </button>
        </form>

        <div className="mt-4 text-sm">
          <Link className="text-zinc-900 underline" href={alt.href}>
            {alt.label}
          </Link>
        </div>
      </div>
    </div>
  );
}

