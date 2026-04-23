import Link from "next/link";
import { ShieldCheck, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="mx-auto max-w-md text-center">
        <Link
          href="/"
          className="mb-10 inline-flex items-center gap-2 font-serif text-lg font-semibold"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <ShieldCheck className="h-4 w-4" aria-hidden />
          </span>
          ClaimGuard
        </Link>

        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          404 · Nicht gefunden
        </p>
        <h1 className="mt-3 font-serif text-4xl leading-tight tracking-tight">
          Diesen Claim kennen wir nicht.
        </h1>
        <p className="mt-4 text-sm text-muted-foreground">
          Die Seite, die du suchst, existiert nicht oder wurde verschoben. Zurück
          zur Startseite oder direkt ins Tool?
        </p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href="/">
              <ArrowLeft className="mr-1.5 h-3.5 w-3.5" aria-hidden />
              Startseite
            </Link>
          </Button>
          <Button size="sm" asChild>
            <Link href="/app">Zum Workspace</Link>
          </Button>
        </div>
      </div>
    </main>
  );
}
