"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowLeft, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthShell } from "@/components/auth/auth-shell";
import { supabase } from "@/lib/supabase";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);

    // Whatever Supabase returns we show the same success screen — that
    // avoids leaking whether an email is registered (spec edge case).
    await supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: `${window.location.origin}/reset-password`,
    });

    setLoading(false);
    setSubmitted(true);
  }

  return (
    <AuthShell
      title="Passwort zurücksetzen"
      subtitle="Wir schicken dir einen Link zum Zurücksetzen an deine E-Mail-Adresse."
    >
      {submitted ? (
        <div className="mt-6 rounded-lg border border-status-allowed/25 bg-status-allowed-bg p-4 text-sm text-status-allowed">
          Falls ein Account zu dieser Adresse existiert, haben wir einen
          Reset-Link versandt. Bitte prüfe dein Postfach.
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email" className="text-xs">
              E-Mail
            </Label>
            <div className="relative">
              <Mail
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden
              />
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="julia@apothera.de"
                className="h-10 pl-9"
                autoComplete="email"
                required
              />
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Wird versendet…" : "Reset-Link senden"}
          </Button>
        </form>
      )}

      <Link
        href="/login"
        className="mt-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
        Zurück zum Login
      </Link>
    </AuthShell>
  );
}
