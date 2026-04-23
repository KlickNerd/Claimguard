import Link from "next/link";
import { ArrowRight, Check, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DemoWidget } from "@/components/site/demo-widget";

const LEGAL_CONTEXT = ["HCVO 1924/2006", "LMIV", "LFGB", "UWG", "aktuelle Rechtsprechung"];

const TRUST = [
  "Hosting & Daten in Deutschland",
  "Zero-Retention bei AI-Anbietern",
  "Kein Ersatz für Rechtsberatung",
];

export function Hero() {
  return (
    <section className="relative overflow-hidden pt-12 pb-20 sm:pt-16">
      <div className="container">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
            <Sparkles className="h-3 w-3 text-primary" aria-hidden />
            {LEGAL_CONTEXT.join(" · ")}
          </span>

          <h1 className="mt-8 font-serif text-5xl leading-[1.05] text-foreground text-balance sm:text-6xl md:text-7xl">
            Health Claims,{" "}
            <span className="italic">die vor Gericht&nbsp;halten.</span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground text-pretty">
            ClaimGuard prüft Werbeaussagen für Supplements und Functional Food gegen die
            EU-Health-Claims-Verordnung – inklusive impliziter Aussagen, mit Rechtsgrundlage
            und Reformulierung.
          </p>

          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button size="lg" asChild>
              <a href="#waitlist">
                Beta-Zugang anfragen
                <ArrowRight className="ml-1.5 h-4 w-4" aria-hidden />
              </a>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="#demo">Live-Demo ansehen</Link>
            </Button>
          </div>

          <ul className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
            {TRUST.map((t) => (
              <li key={t} className="inline-flex items-center gap-1.5">
                <Check className="h-3.5 w-3.5 text-primary" aria-hidden />
                {t}
              </li>
            ))}
          </ul>
        </div>

        <div id="demo" className="mt-16 scroll-mt-24">
          <DemoWidget />
        </div>
      </div>
    </section>
  );
}
