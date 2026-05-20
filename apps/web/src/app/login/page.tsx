"use client";

import { Suspense, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthShell } from "@/components/auth/auth-shell";
import { GoogleButton } from "@/components/auth/google-button";
import { supabase } from "@/lib/supabase";

// useSearchParams() needs a <Suspense> wrapper, otherwise Next.js
// bails out of static prerender and the build fails.
export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginInner />
    </Suspense>
  );
}

function LoginInner() {
  const router = useRouter();
  const params = useSearchParams();
  const redirectTo = params.get("redirect") ?? "/app";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error: signInError } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });

    if (signInError) {
      // Generic message - no user enumeration via different errors for
      // "no account" vs. "wrong password".
      setError("E-Mail oder Passwort ungültig.");
      setLoading(false);
      return;
    }

    // The middleware will pick up the new session cookie and let the
    // /app route through; router.refresh() makes sure server components
    // re-render with the new auth state.
    router.push(redirectTo);
    router.refresh();
  }

  return (
    <AuthShell
      title="Einloggen"
      subtitle="Weiter zu deinem Workspace."
      footer={
        <>
          Noch keinen Account?{" "}
          <Link
            href="/register"
            className="text-foreground underline underline-offset-4"
          >
            Registrieren
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email" className="text-xs">
            E-Mail
          </Label>
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="julia@apothera.de"
            className="h-10"
            autoComplete="email"
            required
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="password" className="text-xs">
              Passwort
            </Label>
            <Link
              href="/forgot-password"
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Vergessen?
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="h-10"
            autoComplete="current-password"
            required
          />
        </div>

        {error ? (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-md border border-status-forbidden/30 bg-status-forbidden-bg p-3 text-sm text-status-forbidden"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <span>{error}</span>
          </div>
        ) : null}

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Einloggen…" : "Einloggen"}
        </Button>
      </form>

      <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
        <div className="h-px flex-1 bg-border" />
        oder
        <div className="h-px flex-1 bg-border" />
      </div>

      <GoogleButton redirectTo={redirectTo} />
    </AuthShell>
  );
}
