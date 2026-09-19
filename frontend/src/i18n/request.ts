import { getRequestConfig } from "next-intl/server";

import { routing } from "./routing";

function isLocale(value: string | null | undefined): value is (typeof routing.locales)[number] {
  return typeof value === "string" && (routing.locales as readonly string[]).includes(value);
}

export default getRequestConfig(async ({ requestLocale }) => {
  const candidate = await requestLocale;
  const locale = isLocale(candidate) ? candidate : routing.defaultLocale;

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});

