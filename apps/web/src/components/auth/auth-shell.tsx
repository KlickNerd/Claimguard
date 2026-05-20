// Shared visual shell for every auth page (login, register, forgot,
// reset, verify-email). Holds the ClaimGuard wordmark + card frame so
// the individual pages only carry the form body.

import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
};

export function AuthShell({ title, subtitle, children, footer }: Props) {
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
          <h1 className="font-serif text-2xl leading-tight tracking-tight">{title}</h1>
          {subtitle ? (
            <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
          ) : null}
          {children}
        </div>

        {footer ? <p className="mt-6 text-center text-xs text-muted-foreground">{footer}</p> : null}
      </div>
    </main>
  );
}
