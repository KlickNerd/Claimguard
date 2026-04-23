"use client";

import { Bell, HelpCircle, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

type Crumb = { label: string; href?: string };

type Props = {
  crumbs: Crumb[];
};

export function AppHeader({ crumbs }: Props) {
  return (
    <header className="flex h-16 items-center justify-between gap-4 border-b border-border/60 bg-background px-6">
      <nav aria-label="Breadcrumb" className="min-w-0">
        <ol className="flex items-center gap-2 truncate text-sm">
          {crumbs.map((c, i) => {
            const last = i === crumbs.length - 1;
            return (
              <li key={i} className="flex items-center gap-2">
                {i > 0 && <span className="text-muted-foreground/50">/</span>}
                <span
                  className={cn(
                    last
                      ? "font-medium text-foreground"
                      : "text-muted-foreground",
                  )}
                >
                  {c.label}
                </span>
              </li>
            );
          })}
        </ol>
      </nav>

      <div className="flex items-center gap-3">
        <div className="relative hidden md:block">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input
            type="search"
            placeholder="Prüfungen, Claims, Quellen"
            className="h-9 w-[280px] pl-8 pr-12 text-sm"
          />
          <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded border border-border/70 bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
            ⌘K
          </kbd>
        </div>

        <button
          type="button"
          aria-label="Hilfe"
          className="grid h-9 w-9 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <HelpCircle className="h-4 w-4" aria-hidden />
        </button>

        <button
          type="button"
          aria-label="Benachrichtigungen"
          className="relative grid h-9 w-9 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <Bell className="h-4 w-4" aria-hidden />
          <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-status-forbidden" />
        </button>

        <span
          className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground"
          aria-label="Eingeloggt als Julia M."
        >
          JM
        </span>
      </div>
    </header>
  );
}
