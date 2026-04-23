import { ScrollText } from "lucide-react";
import { AppHeader } from "@/components/app/app-header";
import { LEGAL_SOURCES_APP } from "@/lib/mock-analyses";

export default function SourcesPage() {
  return (
    <>
      <AppHeader crumbs={[{ label: "Workspace" }, { label: "Rechtsquellen" }]} />

      <div className="flex-1 px-6 py-8 lg:px-10">
        <div className="flex flex-col gap-6">
          <div>
            <h1 className="font-serif text-3xl leading-tight tracking-tight">
              Rechtsquellen
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              Die Bewertung jedes Claims verweist auf Primärquellen. Urteile liegen
              ausschließlich als eigene Paraphrasen vor.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {LEGAL_SOURCES_APP.map((src) => (
              <article
                key={src.title}
                className="rounded-xl border border-border/70 bg-card p-5"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="grid h-9 w-9 place-items-center rounded-lg bg-accent text-accent-foreground">
                    <ScrollText className="h-4 w-4" aria-hidden />
                  </span>
                  <span className="rounded-full bg-muted/60 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    {src.badge}
                  </span>
                </div>
                <h3 className="mt-4 font-serif text-base font-semibold tracking-tight">
                  {src.title}
                </h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {src.subtitle}
                </p>
                <div className="mt-4 font-mono text-xs text-foreground">
                  {src.items.toLocaleString("de-DE")} Einträge
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
