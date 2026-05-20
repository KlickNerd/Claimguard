// Final landing for both flows that hand back a ``?code=`` param:
//   - Google OAuth (after the user confirms in the Google popup)
//   - Email confirmation (after the user clicks the link in the
//     verification mail)
//
// Supabase ships the code in the URL, we exchange it for a session
// cookie via ``exchangeCodeForSession``, then bounce the user wherever
// they were headed (``?next=``) or to the workspace by default.

import { NextResponse, type NextRequest } from "next/server";
import { cookies } from "next/headers";
import { createServerClientFromCookies } from "@/lib/supabase-server";

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next") ?? "/app";

  if (!code) {
    // Either an OAuth provider denied, or the user landed here without
    // a code. Send them back to login with a generic note.
    const loginUrl = new URL("/login?error=oauth_failed", url.origin);
    return NextResponse.redirect(loginUrl);
  }

  const cookieStore = await cookies();
  const supabase = createServerClientFromCookies(cookieStore);
  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    const loginUrl = new URL("/login?error=oauth_failed", url.origin);
    return NextResponse.redirect(loginUrl);
  }

  // ``next`` is always a relative path we control — refuse anything
  // else as a defense against open-redirect abuse.
  const safeNext = next.startsWith("/") && !next.startsWith("//") ? next : "/app";
  return NextResponse.redirect(new URL(safeNext, url.origin));
}
