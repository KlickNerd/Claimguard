import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
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
            Einloggen
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Weiter zu deinem Workspace.
          </p>

          <form className="mt-6 space-y-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email" className="text-xs">
                E-Mail
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="julia@apothera.de"
                className="h-10"
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
                placeholder="••••••••"
                className="h-10"
                required
              />
            </div>

            <Button className="w-full" asChild>
              <Link href="/app">Einloggen</Link>
            </Button>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
            <div className="h-px flex-1 bg-border" />
            oder
            <div className="h-px flex-1 bg-border" />
          </div>

          <Button variant="outline" className="w-full" asChild>
            <Link href="/app">Mit Google fortfahren</Link>
          </Button>
        </div>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Noch keinen Account?{" "}
          <Link href="/#waitlist" className="text-foreground underline underline-offset-4">
            Beta-Zugang anfragen
          </Link>
        </p>
      </div>
    </main>
  );
}
