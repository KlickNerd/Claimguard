"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthShell } from "@/components/auth/auth-shell";
import {
  PasswordStrength,
  getPasswordScore,
} from "@/components/auth/password-strength";
import { supabase } from "@/lib/supabase";

const MIN_PASSWORD_LENGTH = 12;
const MIN_PASSWORD_SCORE = 3;

export default function ResetPasswordPage() {
  // Supabase puts the recovery session in the URL fragment when the
  // user clicks the email link. The Supabase JS client picks that up
  // automatically and we end up with a temporary session that lets us
  // call updateUser({ password }). No need to parse the fragment here.

  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const passwordScore = getPasswordScore(password);
  const passwordOk =
    password.length >= MIN_PASSWORD_LENGTH && passwordScore >= MIN_PASSWORD_SCORE;
  const matches = password === confirm;

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    if (!passwordOk) {
      setError(
        `Bitte ein Passwort mit mindestens ${MIN_PASSWORD_LENGTH} Zeichen und ausreichender Stärke wählen.`,
      );
      return;
    }
    if (!matches) {
      setError("Die beiden Passwörter stimmen nicht überein.");
      return;
    }

    setLoading(true);
    const { error: updateError } = await supabase.auth.updateUser({
      password,
    });
    setLoading(false);

    if (updateError) {
      setError(
        "Reset-Link ungültig oder abgelaufen. Bitte einen neuen Link anfordern.",
      );
      return;
    }

    router.push("/login?reset=success");
  }

  return (
    <AuthShell
      title="Neues Passwort"
      subtitle="Wähle ein neues, sicheres Passwort für deinen Account."
    >
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="password" className="text-xs">
            Neues Passwort
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

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="confirm" className="text-xs">
            Passwort wiederholen
          </Label>
          <Input
            id="confirm"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="h-10"
            autoComplete="new-password"
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

        <Button
          type="submit"
          className="w-full"
          disabled={loading || !passwordOk || !matches || !confirm}
        >
          {loading ? "Wird gespeichert…" : "Passwort speichern"}
        </Button>
      </form>

      <Link
        href="/login"
        className="mt-6 inline-block text-sm text-muted-foreground hover:text-foreground"
      >
        Zurück zum Login
      </Link>
    </AuthShell>
  );
}
