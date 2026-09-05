"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { ChevronDown } from "lucide-react";

import { usePathname, useRouter } from "@/i18n/navigation";

export function LocaleSwitcher() {
  const tNav = useTranslations("nav");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const [pending, setPending] = useState(false);

  async function onChange(nextLocale: "ru" | "en") {
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

  return (
    <label className="flex items-center gap-2 text-sm text-muted-foreground">
      {/* <span className="hidden sm:inline">{tNav("language")}</span> */}
      <span className="relative inline-flex">
        <select
          className="h-9 appearance-none rounded-full border border-border/80 bg-secondary pl-3 pr-8 text-sm text-foreground"
          disabled={pending}
          value={locale}
          onChange={(e) => onChange(e.target.value === "en" ? "en" : "ru")}
        >
          <option value="ru">{tCommon("ru")}</option>
          <option value="en">{tCommon("en")}</option>
        </select>
        <ChevronDown
          aria-hidden
          className="pointer-events-none absolute right-2.5 top-1/2 size-3.5 -translate-y-1/2 text-foreground"
        />
      </span>
    </label>
  );
}

