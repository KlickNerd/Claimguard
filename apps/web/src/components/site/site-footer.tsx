import Link from "next/link";
import { ShieldCheck, FileText } from "lucide-react";

const PRODUCT_LINKS = [
  { href: "#features", label: "Funktionen" },
  { href: "#pricing", label: "Preise" },
  { href: "#sources", label: "Rechtsquellen" },
  { href: "#api", label: "API-Dokumentation" },
];

const LEGAL_LINKS = [
  { href: "/impressum", label: "Impressum" },
  { href: "/datenschutz", label: "Datenschutz" },
  { href: "/agb", label: "AGB" },
  { href: "/dpa", label: "DPA" },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-border/60 bg-background">
      <div className="container py-12">
        <div className="grid grid-cols-1 gap-10 md:grid-cols-[1.5fr_1fr_1fr]">
          <div>
            <Link
              href="/"
              className="flex items-center gap-2 font-serif text-base font-semibold"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <ShieldCheck className="h-4 w-4" aria-hidden />
              </span>
              ClaimGuard
            </Link>
            <p className="mt-4 max-w-sm text-sm leading-relaxed text-muted-foreground">
              ClaimGuard ist ein Assistenzsystem zur Compliance-Prüfung gesundheitsbezogener
              Werbeaussagen. <strong className="font-semibold text-foreground">Keine Rechtsberatung.</strong>{" "}
              Im Zweifelsfall einen Fachanwalt für Wettbewerbsrecht konsultieren.
            </p>
          </div>

          <nav aria-labelledby="footer-product">
            <h3
              id="footer-product"
              className="text-sm font-semibold text-foreground"
            >
              Produkt
            </h3>
            <ul className="mt-4 space-y-2.5 text-sm text-muted-foreground">
              {PRODUCT_LINKS.map((link) => (
                <li key={link.href}>
                  <a href={link.href} className="transition-colors hover:text-foreground">
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          <nav aria-labelledby="footer-legal">
            <h3
              id="footer-legal"
              className="text-sm font-semibold text-foreground"
            >
              Rechtliches
            </h3>
            <ul className="mt-4 space-y-2.5 text-sm text-muted-foreground">
              {LEGAL_LINKS.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="transition-colors hover:text-foreground">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-3 border-t border-border/60 pt-6 text-xs text-muted-foreground md:flex-row md:items-center">
          <span>© {new Date().getFullYear()} ClaimGuard. Hosted in Frankfurt am Main.</span>
          <span className="flex items-center gap-2">
            <FileText className="h-3.5 w-3.5" aria-hidden />
            HCVO 1924/2006 · LMIV · LFGB · UWG
          </span>
        </div>
      </div>
    </footer>
  );
}
