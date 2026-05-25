"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ChevronsUpDown,
  ClipboardPlus,
  Clock,
  LogOut,
  ScrollText,
  Sparkles,
  Users,
  Settings,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/lib/auth-context";
import { WORKSPACE } from "@/lib/mock-analyses";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  badge?: string | number;
  comingSoon?: boolean;
};

const NAV: NavItem[] = [
  { href: "/app", label: "Neue Prüfung", icon: ClipboardPlus },
  { href: "/app/history", label: "Verlauf", icon: Clock, badge: 248 },
  { href: "/app/sources", label: "Rechtsquellen", icon: ScrollText },
  { href: "/app/team", label: "Team", icon: Users, comingSoon: true },
  { href: "/app/settings", label: "Einstellungen", icon: Settings },
];

export function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, signOut } = useAuth();

  const email = user?.email ?? "";
  const initial = (email[0] ?? "?").toUpperCase();

  async function handleSignOut() {
    await signOut();
    router.replace("/login");
  }

  return (
    <aside className="sticky top-0 flex h-screen w-[240px] shrink-0 flex-col border-r border-border/60 bg-sidebar text-sidebar-foreground">
      <div className="flex items-center gap-2 px-4 py-4">
        <Link
          href="/"
          className="flex items-center gap-2 font-serif text-base font-semibold"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <ShieldCheck className="h-4 w-4" aria-hidden />
          </span>
          ClaimGuard
        </Link>
      </div>

      {/* Workspace Card */}
      <div className="px-3">
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-lg border border-sidebar-border bg-background px-2.5 py-2 text-left transition-colors hover:bg-sidebar-accent"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-[11px] font-semibold text-primary-foreground">
            {WORKSPACE.initials}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium">
              {WORKSPACE.name}
            </span>
            <span className="block text-[11px] text-muted-foreground">
              {WORKSPACE.plan} · {WORKSPACE.members} Members
            </span>
          </span>
          <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
        </button>
      </div>

      <div className="px-3 py-3">
        <Button className="w-full" size="sm" asChild>
          <Link href="/app">
            <ClipboardPlus className="mr-1.5 h-3.5 w-3.5" aria-hidden />
            Neue Prüfung
          </Link>
        </Button>
      </div>

      <nav className="flex-1 px-2">
        <div className="px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Workspace
        </div>
        <ul className="space-y-0.5">
          {NAV.map((item) => {
            const active =
              item.href === "/app"
                ? pathname === "/app"
                : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "group flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors",
                    active
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" aria-hidden />
                  <span className="flex-1 truncate">{item.label}</span>
                  {item.badge && (
                    <span className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                      {item.badge}
                    </span>
                  )}
                  {item.comingSoon && (
                    <span className="rounded-full bg-accent px-1.5 py-0.5 text-[10px] font-medium text-accent-foreground">
                      V1.1
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Plan-Widget */}
      <div className="m-3 rounded-lg border border-sidebar-border bg-accent/60 p-3">
        <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-accent-foreground">
          <Sparkles className="h-3.5 w-3.5" aria-hidden />
          {WORKSPACE.plan}-Plan
        </div>
        <div className="mb-1 flex items-center justify-between text-[11px] text-muted-foreground">
          <span>Prüfungen</span>
          <span className="font-mono">
            {WORKSPACE.usage.used} / {WORKSPACE.usage.limit.toLocaleString("de-DE")}
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-background">
          <div
            className="h-full bg-primary"
            style={{
              width: `${(WORKSPACE.usage.used / WORKSPACE.usage.limit) * 100}%`,
            }}
          />
        </div>
        <Button variant="ghost" size="sm" className="mt-2 w-full text-xs">
          Plan upgraden
        </Button>
      </div>

      {/* Account-Footer */}
      <div className="border-t border-sidebar-border px-3 py-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-sidebar-accent"
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-[12px] font-semibold text-primary-foreground">
                {initial}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">
                  {email || "Lade…"}
                </span>
                <span className="block text-[11px] text-muted-foreground">
                  Account
                </span>
              </span>
              <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" side="top" className="w-56">
            <DropdownMenuLabel className="truncate">{email}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={handleSignOut}>
              <LogOut className="mr-2 h-4 w-4" aria-hidden />
              Abmelden
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </aside>
  );
}
