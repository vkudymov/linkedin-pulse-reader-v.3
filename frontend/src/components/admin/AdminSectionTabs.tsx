import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";

const tabActive =
  "rounded-full border border-border bg-card px-4 py-2 text-sm text-foreground";
const tabInactive =
  "rounded-full border border-border/60 px-4 py-2 text-sm text-muted-foreground hover:text-foreground";

export async function AdminSectionTabs({
  active,
}: {
  active: "users" | "searchRuns" | "searches" | "prompts" | "settings";
}) {
  const t = await getTranslations("admin");

  return (
    <div className="mb-6 flex flex-wrap gap-2">
      <Link href="/admin" className={active === "users" ? tabActive : tabInactive}>
        {t("tabs.users")}
      </Link>
      <Link href="/admin/search-runs" className={active === "searchRuns" ? tabActive : tabInactive}>
        {t("tabs.searchRuns")}
      </Link>
      <Link href="/admin/searches" className={active === "searches" ? tabActive : tabInactive}>
        {t("tabs.searches")}
      </Link>
      <Link href="/admin/prompts" className={active === "prompts" ? tabActive : tabInactive}>
        {t("tabs.prompts")}
      </Link>
      <Link href="/admin/settings" className={active === "settings" ? tabActive : tabInactive}>
        {t("tabs.settings")}
      </Link>
    </div>
  );
}
