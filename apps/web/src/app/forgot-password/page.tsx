"use client";

import { useState } from "react";
import Link from "next/link";
import { ShieldCheck, ArrowLeft, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <Link
          href="/"
          className="mb-10 flex items-center justify-center gap-2 font-serif text-lg font-semibold"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <ShieldCheck className="h-4 w-4" aria-hidden />
          </span>
          ClaimGuard
        </Link>

        <div className="rounded-2xl border border-border/70 bg-card p-8 shadow-sm">
          <h1 className="font-serif text-2xl leading-tight tracking-tight">
            Passwort zurücksetzen
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Wir schicken dir einen Link zum Zurücksetzen an deine E-Mail-Adresse.
          </p>

          {submitted ? (
            <div className="mt-6 rounded-lg border border-status-allowed/25 bg-status-allowed-bg p-4 text-sm text-status-allowed">
              Falls ein Account zu dieser Adresse existiert, haben wir einen
              Reset-Link versandt. Bitte prüfe dein Postfach.
            </div>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setSubmitted(true);
              }}
              className="mt-6 space-y-4"
            >
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
                    placeholder="julia@apothera.de"
                    className="h-10 pl-9"
                    required
                  />
                </div>
              </div>

              <Button className="w-full" type="submit">
                Reset-Link senden
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
        </div>
      </div>
    </main>
  );
}
