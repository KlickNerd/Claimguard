const STEPS = [
  {
    n: "01",
    title: "Text einfügen",
    body:
      "Copy-Paste, URL oder PDF-Upload. Auch lange Produktseiten werden in einem Lauf verarbeitet.",
  },
  {
    n: "02",
    title: "Detection & Bewertung",
    body:
      "Claude Sonnet identifiziert Claims, hybrides Retrieval zieht passende Rechtsquellen, Claude Opus bewertet jeden Claim einzeln.",
  },
  {
    n: "03",
    title: "Ampel-Report",
    body:
      "Grün, Gelb, Rot, Grau – mit Begründung, zitierter Rechtsgrundlage und konkretem Reformulierungsvorschlag.",
  },
];

export function HowItWorks() {
  return (
    <section id="how" className="bg-background scroll-mt-20">
      <div className="container py-20">
        <div className="mx-auto max-w-2xl text-center">
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            So funktioniert's
          </span>
          <h2 className="mt-4 font-serif text-4xl leading-tight text-balance sm:text-5xl">
            Vom Werbetext zum belastbaren Report{" "}
            <span className="italic">in unter 60 Sekunden.</span>
          </h2>
        </div>

        <ol className="mt-14 grid grid-cols-1 gap-4 md:grid-cols-3">
          {STEPS.map((s) => (
            <li
              key={s.n}
              className="rounded-xl border border-border/70 bg-card p-6"
            >
              <div className="font-mono text-xs text-primary">{s.n}</div>
              <h3 className="mt-3 font-serif text-lg font-semibold tracking-tight">
                {s.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {s.body}
              </p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
