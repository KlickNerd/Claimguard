import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

const NAV = [
  { href: "#features", label: "Funktionen" },
  { href: "#how", label: "So funktioniert's" },
  { href: "#sources", label: "Rechtsquellen" },
  { href: "#pricing", label: "Preise" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur">
      <div className="container flex h-16 items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 font-serif text-lg font-semibold tracking-tight text-foreground"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <ShieldCheck className="h-4 w-4" aria-hidden />
          </span>
          ClaimGuard
        </Link>

        <nav className="hidden items-center gap-8 text-sm text-muted-foreground md:flex">
          {NAV.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="transition-colors hover:text-foreground"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="hidden sm:inline-flex" asChild>
            <Link href="/login">Login</Link>
          </Button>
          <Button size="sm" asChild>
            <a href="#waitlist">Beta anfragen</a>
          </Button>
        </div>
      </div>
    </header>
  );
}
