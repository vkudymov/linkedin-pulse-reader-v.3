import { NextResponse, type NextRequest } from "next/server";
import createMiddleware from "next-intl/middleware";

import { updateSession } from "./src/lib/supabase/middleware";
import { log } from "./src/lib/log/logger";
import { routing } from "./src/i18n/routing";

const intlMiddleware = createMiddleware(routing);

function stripLocalePrefix(pathname: string): { locale: string; path: string } {
  const parts = pathname.split("/").filter(Boolean);
  const maybeLocale = parts[0] || "";
  const isLocale = routing.locales.includes(maybeLocale as any);
  const locale = isLocale ? maybeLocale : routing.defaultLocale;
  const rest = isLocale ? parts.slice(1) : parts;
  const path = `/${rest.join("/")}`;
  return { locale, path: path === "/" ? "/" : path.replace(/\/+$/, "") };
}

export async function middleware(request: NextRequest) {
  // 1) Locale routing / redirects.
  let response = intlMiddleware(request);

  // 2) Supabase session cookies + user (if any).
  let user: unknown;
  try {
    ({ response, user } = await updateSession(request, response));
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "middleware error";
    log.error("middleware", message, {
      where: "frontend/middleware.ts",
      meta: { path: request.nextUrl.pathname },
    });
    throw e;
  }

  const { pathname } = request.nextUrl;
  const { locale, path } = stripLocalePrefix(pathname);

  // Keep NEXT_LOCALE in sync for RootLayout <html lang=...>.
  try {
    response.cookies.set("NEXT_LOCALE", locale, { path: "/" });
  } catch {
    // Ignore cookie write errors (best-effort).
  }

  const isProtected =
    path.startsWith("/posts") ||
    path.startsWith("/account") ||
    path.startsWith("/prompts") ||
    path.startsWith("/admin");

  if (isProtected && !user) {
    log.warn("middleware", "redirect /posts -> /login", {
      where: "frontend/middleware.ts",
      meta: { path: pathname },
    });
    const url = request.nextUrl.clone();
    url.pathname = `/${locale}/login`;
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  return response;
}

export const config = {
  matcher: [
    // Match all pathnames except for:
    // - API routes
    // - static files
    // - Next.js internals
    "/((?!api|_next|.*\\..*).*)",
  ],
};

