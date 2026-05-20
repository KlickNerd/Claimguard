// Server-side Supabase client.
//
// Use this in Server Components, Route Handlers, and the middleware -
// anywhere that needs to read/write the auth session via cookies. The
// difference vs. ``supabase.ts`` (browser client): this one wires the
// Next.js cookies() API into Supabase so session cookies survive SSR
// boundaries.
//
// Two flavours:
//   - createServerClientFromCookies(cookieStore)  — for Server
//     Components / Route Handlers (call ``cookies()`` and hand it in).
//   - createServerClientForMiddleware(request, response) — for
//     ``middleware.ts``, which has a different request/response shape.

import { createServerClient, type CookieOptions } from "@supabase/ssr";
import type { NextRequest, NextResponse } from "next/server";

type CookieStore = {
  get: (name: string) => { value: string } | undefined;
  set?: (name: string, value: string, options: CookieOptions) => void;
};

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

function assertEnv(): void {
  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error(
      "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY",
    );
  }
}

export function createServerClientFromCookies(cookieStore: CookieStore) {
  assertEnv();
  return createServerClient(supabaseUrl!, supabaseAnonKey!, {
    cookies: {
      get(name: string) {
        return cookieStore.get(name)?.value;
      },
      set(name: string, value: string, options: CookieOptions) {
        // In Server Components (RSC), the cookies() store is read-only.
        // Supabase calls ``set`` to refresh tokens, but the actual write
        // happens via middleware. We swallow the error here so RSCs can
        // still call ``supabase.auth.getUser()`` without crashing.
        try {
          cookieStore.set?.(name, value, options);
        } catch {
          // expected in RSC context
        }
      },
      remove(name: string, options: CookieOptions) {
        try {
          cookieStore.set?.(name, "", { ...options, maxAge: 0 });
        } catch {
          // expected in RSC context
        }
      },
    },
  });
}

export function createServerClientForMiddleware(
  request: NextRequest,
  response: NextResponse,
) {
  assertEnv();
  return createServerClient(supabaseUrl!, supabaseAnonKey!, {
    cookies: {
      get(name: string) {
        return request.cookies.get(name)?.value;
      },
      set(name: string, value: string, options: CookieOptions) {
        response.cookies.set({ name, value, ...options });
      },
      remove(name: string, options: CookieOptions) {
        response.cookies.set({ name, value: "", ...options, maxAge: 0 });
      },
    },
  });
}
