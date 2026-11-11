"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";
import { usePathname, useRouter } from "@/i18n/navigation";

function useLocaleSwitch() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [pending, setPending] = useState(false);

  async function switchLocale(nextLocale: "ru" | "en") {
    if (nextLocale === locale) return;
    setPending(true);
    try {
      await fetch("/api/account/locale", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ locale: nextLocale }),
      });
    } catch {
      // Best-effort: cookie may still be updated by next-intl middleware + navigation.
    } finally {
      setPending(false);
    }

    router.replace(pathname, { locale: nextLocale });
    router.refresh();
  }

  return { locale, pending, switchLocale };
}

export function LocaleMenuButtons({ className }: { className?: string }) {
  const tNav = useTranslations("nav");
  const tCommon = useTranslations("common");
  const { locale, pending, switchLocale } = useLocaleSwitch();

  return (
    <div className={cn("px-3 pb-2 pt-1", className)}>
      <p className="mb-2 text-xs font-medium text-muted-foreground">{tNav("language")}</p>
      <div className="flex gap-1 rounded-lg bg-muted/60 p-1">
        {(["ru", "en"] as const).map((code) => (
          <button
            key={code}
            type="button"
            disabled={pending}
            onClick={() => switchLocale(code)}
            className={cn(
              "flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition-colors",
              locale === code
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {code === "ru" ? tCommon("ru") : tCommon("en")}
          </button>
        ))}
      </div>
    </div>
  );
}

/** @deprecated Standalone select — prefer language inside profile menu. */
export function LocaleSwitcher() {
  const tCommon = useTranslations("common");
  const { locale, pending, switchLocale } = useLocaleSwitch();

  return (
    <span className="relative inline-flex">
      <select
        className="h-9 appearance-none rounded-full border border-border/80 bg-secondary pl-3 pr-8 text-sm text-foreground"
        disabled={pending}
        value={locale}
        onChange={(e) => switchLocale(e.target.value === "en" ? "en" : "ru")}
      >
        <option value="ru">{tCommon("ru")}</option>
        <option value="en">{tCommon("en")}</option>
      </select>
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute right-2.5 top-1/2 size-3.5 -translate-y-1/2 text-foreground"
      />
    </span>
  );
}
