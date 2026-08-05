import { NextResponse, type NextRequest } from "next/server";

import { updateSession } from "./src/lib/supabase/middleware";
import { log } from "./src/lib/log/logger";

export async function middleware(request: NextRequest) {
  let response: NextResponse;
  let user: unknown;
  try {
    ({ response, user } = await updateSession(request));
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "middleware error";
    log.error("middleware", message, {
      where: "frontend/middleware.ts",
      meta: { path: request.nextUrl.pathname },
    });
    throw e;
  }

  const { pathname } = request.nextUrl;
  const isProtected = pathname.startsWith("/posts") || pathname.startsWith("/account");

  if (isProtected && !user) {
    log.warn("middleware", "redirect /posts -> /login", {
      where: "frontend/middleware.ts",
      meta: { path: pathname },
    });
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  return response;
}

export const config = {
  matcher: ["/posts/:path*", "/account/:path*", "/login", "/register", "/auth/callback"],
};

