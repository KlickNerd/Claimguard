// Next.js middleware that guards every request before it hits a page.
//
// Two jobs:
//   1. Refresh the Supabase session on each request (cookies expire,
//      access tokens rotate; without this the user would get logged
//      out every ~1h).
//   2. Redirect unauthenticated users away from /app/* to /login, and
//      redirect already-logged-in users away from /login + /register
//      back to /app.
//
// The matcher at the bottom limits the middleware to the routes that
// actually need this dance - static assets, favicon, etc. are skipped
// so we don't waste a Supabase call on every CSS file.

import { NextResponse, type NextRequest } from "next/server";
import { createServerClientForMiddleware } from "@/lib/supabase-server";

const PROTECTED_PREFIXES = ["/app"];
const AUTH_ONLY_PREFIXES = ["/login", "/register", "/forgot-password"];

export async function middleware(request: NextRequest) {
  const response = NextResponse.next({ request });

  const supabase = createServerClientForMiddleware(request, response);
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const path = request.nextUrl.pathname;

  const isProtected = PROTECTED_PREFIXES.some((p) => path.startsWith(p));
  const isAuthOnly = AUTH_ONLY_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`));

  if (isProtected && !user) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    // Remember where the user was headed so we can bounce them back
    // after a successful login.
    loginUrl.searchParams.set("redirect", path);
    return NextResponse.redirect(loginUrl);
  }

  if (isAuthOnly && user) {
    const appUrl = request.nextUrl.clone();
    appUrl.pathname = "/app";
    appUrl.search = "";
    return NextResponse.redirect(appUrl);
  }

  return response;
}

export const config = {
  matcher: [
    // Everything except Next internals, static files, the public marketing site assets.
    "/((?!_next/static|_next/image|favicon.ico|images/|fonts/|public/).*)",
  ],
};
