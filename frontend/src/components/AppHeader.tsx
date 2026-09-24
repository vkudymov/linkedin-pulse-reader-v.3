"use client";

import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";

export function AppHeader({
  title,
  subtitle,
  active,
  isAdmin,
}: {
  title: string;
  subtitle?: string | null;
  active?: "posts" | "jobs" | "account" | "prompts" | "searches" | "admin";
  isAdmin?: boolean;
}) {
  const t = useTranslations("nav");
  const isResultsActive = active === "posts" || active === "jobs";
  return (
    <header className="border-b border-border/80 bg-background">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-6 px-6 py-4">
        <div className="min-w-0 shrink">
          <h1 className="truncate text-base font-semibold tracking-tight">{title}</h1>
          {subtitle ? (
            <p className="truncate text-sm text-muted-foreground">{subtitle}</p>
          ) : null}
        </div>
        <nav className="flex shrink-0 items-center gap-3 whitespace-nowrap">
          <Link
            className={[
              "whitespace-nowrap text-sm underline-offset-4 hover:text-foreground hover:underline",
              isResultsActive ? "text-foreground" : "text-muted-foreground",
            ].join(" ")}
            href="/posts"
          >
            {t("results")}
          </Link>

          <Link
            className={[
              "whitespace-nowrap text-sm underline-offset-4 hover:text-foreground hover:underline",
              active === "searches" ? "text-foreground" : "text-muted-foreground",
            ].join(" ")}
            href="/searches"
          >
            {t("searches")}
          </Link>
          <Link
            className={[
              "whitespace-nowrap text-sm underline-offset-4 hover:text-foreground hover:underline",
              active === "prompts" ? "text-foreground" : "text-muted-foreground",
            ].join(" ")}
            href="/prompts"
          >
            {t("prompts")}
          </Link>
          <Link
            className={[
              "whitespace-nowrap text-sm underline-offset-4 hover:text-foreground hover:underline",
              active === "account" ? "text-foreground" : "text-muted-foreground",
            ].join(" ")}
            href="/account"
          >
            {t("account")}
          </Link>
          {isAdmin ? (
            <Link
              className={[
                "whitespace-nowrap text-sm underline-offset-4 hover:text-foreground hover:underline",
                active === "admin" ? "text-foreground" : "text-muted-foreground",
              ].join(" ")}
              href="/admin"
            >
              {t("admin")}
            </Link>
          ) : null}

          <LocaleSwitcher />
          <Link className="whitespace-nowrap text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline" href="/logout">
            {t("logout")}
          </Link>
        </nav>
      </div>
    </header>
  );
}

