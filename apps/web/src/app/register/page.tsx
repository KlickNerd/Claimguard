"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthShell } from "@/components/auth/auth-shell";
import { GoogleButton } from "@/components/auth/google-button";
import {
  PasswordStrength,
  getPasswordScore,
} from "@/components/auth/password-strength";
import { supabase } from "@/lib/supabase";

const MIN_PASSWORD_LENGTH = 12;
const MIN_PASSWORD_SCORE = 3;

export default function RegisterPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const passwordScore = getPasswordScore(password);
  const passwordOk =
    password.length >= MIN_PASSWORD_LENGTH && passwordScore >= MIN_PASSWORD_SCORE;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    if (!passwordOk) {
      setError(
        `Bitte ein Passwort mit mindestens ${MIN_PASSWORD_LENGTH} Zeichen und ausreichender Stärke wählen.`,
      );
      return;
    }

    setLoading(true);

    const { error: signUpError, data } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent("/app")}`,
      },
    });

    setLoading(false);

    if (signUpError) {
      // Generic to prevent user enumeration — Supabase returns "User
      // already registered" in plain text; we hide that.
      setError(
        "Registrierung fehlgeschlagen. Falls du bereits einen Account hast, melde dich bitte an.",
      );
      return;
    }

    // Supabase doesn't auto-sign-in when email-confirmation is required
    // (which it is, per spec). Send the user to a "check your inbox"
    // screen; the link in that mail lands at /auth/callback.
    const verifyUrl = `/verify-email?email=${encodeURIComponent(email.trim())}`;
    router.push(verifyUrl);
    void data;
  }

  return (
    <AuthShell
      title="Registrieren"
      subtitle="Erstelle in zwei Minuten deinen Workspace."
      footer={
        <>
          Schon registriert?{" "}
          <Link
            href="/login"
            className="text-foreground underline underline-offset-4"
          >
            Einloggen
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
          <Label htmlFor="password" className="text-xs">
            Passwort
          </Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="mindestens 12 Zeichen"
            className="h-10"
            autoComplete="new-password"
            minLength={MIN_PASSWORD_LENGTH}
            required
          />
          <PasswordStrength password={password} />
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

        <Button type="submit" className="w-full" disabled={loading || !passwordOk}>
          {loading ? "Konto wird erstellt…" : "Konto erstellen"}
        </Button>

        <p className="text-xs text-muted-foreground">
          Mit der Registrierung akzeptierst du die{" "}
          <Link href="/agb" className="underline underline-offset-4">AGB</Link>{" "}
          und{" "}
          <Link href="/datenschutz" className="underline underline-offset-4">
            Datenschutzbestimmungen
          </Link>
          .
        </p>
      </form>

      <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
        <div className="h-px flex-1 bg-border" />
        oder
        <div className="h-px flex-1 bg-border" />
      </div>

      <GoogleButton label="Mit Google registrieren" />
    </AuthShell>
  );
}
