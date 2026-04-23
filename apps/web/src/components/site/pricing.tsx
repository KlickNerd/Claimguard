import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Plan = {
  name: string;
  audience: string;
  price: string;
  priceSuffix?: string;
  cta: string;
  features: string[];
  highlight?: boolean;
};

const PLANS: Plan[] = [
  {
    name: "Starter",
    audience: "Für Solo-Brands",
    price: "29€",
    priceSuffix: "/ Monat",
    cta: "Beta-Zugang",
    features: ["100 Prüfungen / Monat", "Text- und URL-Eingabe", "PDF-Export"],
  },
  {
    name: "Studio",
    audience: "Für Agenturen & wachsende Brands",
    price: "99€",
    priceSuffix: "/ Monat",
    cta: "Beta-Zugang",
    highlight: true,
    features: [
      "1.000 Prüfungen / Monat",
      "Batch-Verarbeitung",
      "Team-Workspaces (V1.1)",
      "Versionierung (V1.1)",
    ],
  },
  {
    name: "Enterprise",
    audience: "Mit API & SLA",
    price: "Custom",
    cta: "Sales kontaktieren",
    features: [
      "Unbegrenzte Prüfungen",
      "REST-API (V1.2)",
      "DPA & EU-Hosting-Garantie",
      "Dedicated Support",
    ],
  },
];

export function Pricing() {
  return (
    <section id="pricing" className="bg-background scroll-mt-20">
      <div className="container py-20">
        <div className="mx-auto max-w-2xl text-center">
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Preise
          </span>
          <h2 className="mt-4 font-serif text-4xl leading-tight text-balance sm:text-5xl">
            Faire Preise für jede <span className="italic">Größe.</span>
          </h2>
          <p className="mt-4 text-base leading-relaxed text-muted-foreground">
            Endgültige Tarife folgen mit dem Public Launch. Beta-Nutzer erhalten 50 %
            Rabatt im ersten Jahr.
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-6 lg:grid-cols-3 lg:items-stretch">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={cn(
                "relative flex flex-col rounded-xl border bg-card p-6 shadow-sm",
                plan.highlight
                  ? "border-primary/30 shadow-lg ring-1 ring-primary/20"
                  : "border-border/70",
              )}
            >
              {plan.highlight && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3 py-1 text-[11px] font-medium text-primary-foreground">
                  Beliebteste Wahl
                </span>
              )}

              <div>
                <h3 className="font-serif text-2xl font-semibold tracking-tight">
                  {plan.name}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">{plan.audience}</p>
              </div>

              <div className="mt-6 flex items-end gap-1">
                <span className="font-serif text-5xl font-semibold leading-none tracking-tight">
                  {plan.price}
                </span>
                {plan.priceSuffix && (
                  <span className="pb-1.5 text-sm text-muted-foreground">
                    {plan.priceSuffix}
                  </span>
                )}
              </div>

              <ul className="mt-6 space-y-2.5 text-sm text-foreground">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>

              <div className="mt-8">
                <Button
                  variant={plan.highlight ? "default" : "outline"}
                  className="w-full"
                  asChild
                >
                  <a href="#waitlist">{plan.cta}</a>
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
