"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AuthShell } from "@/components/auth/auth-shell";
import { supabase } from "@/lib/supabase";

export default function VerifyEmailPage() {
  const params = useSearchParams();
  const email = params.get("email") ?? "";
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState(false);

  async function handleResend() {
    if (!email) return;
    setResending(true);
    // Supabase has its own per-email rate-limit (1 mail / 60 s); we
    // just rely on that and surface a friendly toast either way.
    await supabase.auth.resend({
      type: "signup",
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent("/app")}`,
      },
    });
    setResending(false);
    setResent(true);
    setTimeout(() => setResent(false), 5000);
  }

  return (
    <AuthShell title="Postfach prüfen" subtitle="Fast geschafft.">
      <div className="mt-6 space-y-4">
        <div className="flex items-start gap-3 rounded-lg border border-border/70 bg-muted/30 p-4">
          <Mail
            className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground"
            aria-hidden
          />
          <div className="text-sm">
            <p className="text-foreground">
              Wir haben dir{email ? <> an <span className="font-medium">{email}</span></> : ""} einen
              Bestätigungs-Link geschickt.
            </p>
            <p className="mt-1 text-muted-foreground">
              Klick den Link in der E-Mail, um dein Konto zu aktivieren. Der Link ist 24 Stunden gültig.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={handleResend}
            disabled={!email || resending || resent}
          >
            {resending
              ? "Wird gesendet…"
              : resent
              ? "Erneut versendet ✓"
              : "Link erneut senden"}
          </Button>

          {resent ? (
            <p className="flex items-center gap-1.5 text-xs text-status-allowed">
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
              Falls deine Adresse registriert ist, ist die Mail unterwegs.
            </p>
          ) : null}
        </div>

        <div className="border-t border-border/70 pt-4 text-xs text-muted-foreground">
          Mail nicht angekommen? Prüfe deinen Spam-Ordner oder{" "}
          <Link href="/register" className="text-foreground underline underline-offset-4">
            registriere dich erneut
          </Link>
          .
        </div>
      </div>
    </AuthShell>
  );
}
