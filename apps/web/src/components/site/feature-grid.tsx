import {
  Brain,
  Scale,
  Wand2,
  Database,
  ShieldCheck,
  Zap,
  type LucideIcon,
} from "lucide-react";

type Feature = {
  icon: LucideIcon;
  title: string;
  body: string;
};

const FEATURES: Feature[] = [
  {
    icon: Brain,
    title: "Implizite Claims erkennen",
    body:
      'Nicht nur „heilt Krankheit X". Auch „für einen energiegeladenen Tag", „Detox-Kur" oder „natürliche Abwehrkräfte" werden als gesundheitsbezogen markiert.',
  },
  {
    icon: Scale,
    title: "Bewertung gegen Primärrecht",
    body:
      "EU-Register, HCVO, LMIV, LFGB, UWG sowie kuratierte BGH-, OLG- und LG-Urteile. Hybride Suche aus Vektor- und Volltext-Retrieval.",
  },
  {
    icon: Wand2,
    title: "Konkrete Reformulierungen",
    body:
      'Statt nur „unzulässig" – jeder problematische Claim erhält einen Vorschlag, der die Werbebotschaft erhält und die zugelassene Wortwahl trifft.',
  },
  {
    icon: Database,
    title: "Aktuelle Rechtslage",
    body:
      "Datenbank wird wöchentlich gepflegt. Neue EFSA-Opinions und Urteile fließen in die Bewertung ein, ohne dass du etwas tun musst.",
  },
  {
    icon: ShieldCheck,
    title: "EU-Hosting, Zero-Retention",
    body:
      "Server in Frankfurt, keine User-Daten in US-Cloud. AI-Anbieter werden mit Zero-Retention-Header angesprochen. DSGVO by design.",
  },
  {
    icon: Zap,
    title: "Text, URL oder PDF",
    body:
      "Prüfe einzelne Claims, ganze Produktseiten oder Broschüren. Inklusive batch-fähiger API für Marketing-Pipelines und Headless-CMS (ab V1.2).",
  },
];

export function FeatureGrid() {
  return (
    <section id="features" className="bg-card scroll-mt-20">
      <div className="container py-20">
        <div className="mx-auto max-w-2xl text-center">
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Was es leistet
          </span>
          <h2 className="mt-4 font-serif text-4xl leading-tight text-balance sm:text-5xl">
            Detection, Bewertung, Reformulierung{" "}
            <span className="italic">– in einem Lauf.</span>
          </h2>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, body }) => (
            <article
              key={title}
              className="rounded-xl border border-border/70 bg-background p-6 transition-shadow hover:shadow-sm"
            >
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                <Icon className="h-5 w-5" aria-hidden />
              </span>
              <h3 className="mt-5 font-serif text-lg font-semibold tracking-tight">
                {title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {body}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
