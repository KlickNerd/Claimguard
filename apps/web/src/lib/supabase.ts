// Browser-side Supabase client.
//
// Used in Client Components ("use client") for sign-in, sign-up, session
// refresh, etc. Reads the project URL + anon key from NEXT_PUBLIC_* env
// vars - both are safe to ship in the browser bundle (RLS protects the
// data, the anon key is by design publishable).
//
// For Server Components, Route Handlers, and Middleware use
// ``supabase-server.ts`` instead, which wires cookies onto the request.

import { createBrowserClient } from "@supabase/ssr";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  // Fail loud at module-load time so a broken deploy doesn't silently
  // hand back a non-functional client at the first sign-in attempt.
  throw new Error(
    "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY. " +
      "Set both in apps/web/.env.local (or the production env).",
  );
}

export const supabase = createBrowserClient(supabaseUrl, supabaseAnonKey);
