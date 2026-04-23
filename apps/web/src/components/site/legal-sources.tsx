import { Check, TriangleAlert } from "lucide-react";

const SOURCES = [
  "EU-Register zugelassener Health Claims (Stand wöchentlich)",
  "Verordnung (EG) 1924/2006 (HCVO) – konsolidierte Fassung",
  "Lebensmittelinformations-Verordnung (LMIV) und LFGB",
  "Über 30 paraphrasierte BGH-, OLG- und LG-Entscheidungen",
  "EFSA Scientific Opinions (botanische Stoffe, On-Hold-Liste)",
];

export function LegalSources() {
  return (
    <section id="sources" className="bg-card scroll-mt-20">
      <div className="container grid grid-cols-1 gap-12 py-20 lg:grid-cols-2 lg:gap-16">
        <div>
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Rechtsquellen
          </span>
          <h2 className="mt-4 font-serif text-4xl leading-tight text-balance sm:text-5xl">
            Kuratiert. Aktuell.{" "}
            <span className="italic">Nachvollziehbar.</span>
          </h2>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground">
            Jede Bewertung verweist auf Primärquellen. Urteile liegen ausschließlich als
            eigene Paraphrasen vor – keine Volltexte aus juris oder beck-online.
          </p>

          <ul className="mt-7 space-y-3 text-sm text-foreground">
            {SOURCES.map((src) => (
              <li key={src} className="flex items-start gap-2.5">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
                <span>{src}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-xl border border-border/70 bg-background p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-status-borderline-bg px-2.5 py-1 text-xs font-medium text-status-borderline">
              <TriangleAlert className="h-3.5 w-3.5" aria-hidden />
              Risiko
            </span>
            <span className="font-mono text-[11px] text-muted-foreground">
              Beispiel-Eintrag
            </span>
          </div>

          <h3 className="mt-4 font-serif text-lg font-semibold tracking-tight">
            „Detox-Kur für Leber und Niere"
          </h3>

          <div className="mt-4">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              Bewertung
            </div>
            <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">
              „Detox" ist nach BGH-Rechtsprechung ein gesundheitsbezogener Claim und im
              EU-Register nicht zugelassen.
            </p>
          </div>

          <div className="mt-4 rounded-md bg-muted/50 p-3 font-mono text-[11px] leading-5 text-foreground/80">
            BGH, Urt. v. 01.09.2016 – I ZR 252/16
            <br />
            Art. 10 Abs. 1 VO (EG) 1924/2006
          </div>

          <div className="mt-4 rounded-md bg-accent/60 p-3">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-accent-foreground/80">
              Reformulierung
            </div>
            <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">
              „Mit Mariendistel und Artischocke – traditionell verwendete Pflanzenstoffe."
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
