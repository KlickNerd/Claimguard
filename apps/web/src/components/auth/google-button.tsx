"use client";

// Google OAuth button. Triggers Supabase's OAuth flow with ``redirectTo``
// pointing at our ``/auth/callback`` route which exchanges the code for
// a session and then sends the user to /app (or wherever they came from).

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { supabase } from "@/lib/supabase";

type Props = {
  label?: string;
  redirectTo?: string;
};

export function GoogleButton({ label = "Mit Google fortfahren", redirectTo }: Props) {
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    setLoading(true);
    const next = redirectTo ?? "/app";
    const callbackUrl = `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`;
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: callbackUrl,
        queryParams: {
          // German OAuth consent screen.
          hl: "de",
          prompt: "select_account",
        },
      },
    });
    if (error) {
      setLoading(false);
      // Surfacing a toast here would need the toast provider already wired;
      // for now we fall back to alert so the user notices.
      alert("Google-Login fehlgeschlagen. Bitte erneut versuchen.");
    }
    // On success the browser navigates away, no need to reset loading.
  }

  return (
    <Button
      type="button"
      variant="outline"
      className="w-full"
      disabled={loading}
      onClick={handleClick}
    >
      <GoogleGlyph />
      {loading ? "Verbinde mit Google…" : label}
    </Button>
  );
}

function GoogleGlyph() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 18 18"
      className="mr-2 h-4 w-4"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M17.64 9.2c0-.638-.057-1.252-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.258h2.91c1.702-1.567 2.682-3.875 2.682-6.615Z"
        fill="#4285F4"
      />
      <path
        d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.909-2.258c-.806.54-1.837.86-3.047.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"
        fill="#34A853"
      />
      <path
        d="M3.964 10.707A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.707V4.96H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.04l3.007-2.333Z"
        fill="#FBBC05"
      />
      <path
        d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.892 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.96L3.964 7.293C4.672 5.166 6.656 3.58 9 3.58Z"
        fill="#EA4335"
      />
    </svg>
  );
}
