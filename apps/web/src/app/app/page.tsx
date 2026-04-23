"use client";

import { useState } from "react";
import {
  Activity,
  Check,
  Download,
  FileText,
  Link2,
  MoreHorizontal,
  RefreshCcw,
  Scan,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  TriangleAlert,
  Upload,
  X,
} from "lucide-react";
import { AppHeader } from "@/components/app/app-header";
import { KpiCard } from "@/components/app/kpi-card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { KPIS } from "@/lib/mock-analyses";
import { DEMO_INPUT } from "@/lib/demo-data";

const TABS = [
  { id: "text" as const, label: "Text", icon: FileText },
  { id: "url" as const, label: "URL", icon: Link2 },
  { id: "pdf" as const, label: "PDF", icon: Upload },
];

export default function AppHomePage() {
  const [activeTab, setActiveTab] = useState<"text" | "url" | "pdf">("text");
  const [input, setInput] = useState(DEMO_INPUT);

  return (
    <>
      <AppHeader
        crumbs={[{ label: "Workspace" }, { label: "Neue Prüfung" }]}
      />

      <div className="flex-1 px-6 py-8 lg:px-10">
        <div className="flex flex-col gap-8">
          {/* Page title + action */}
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="font-serif text-3xl leading-tight tracking-tight">
                Neue Prüfung
              </h1>
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
                Füge Werbetext, Produktseiten-URL oder PDF ein – ClaimGuard
                bewertet jeden Claim gegen die aktuelle Rechtslage.
              </p>
            </div>
            <Button variant="outline" size="sm">
              <Download className="mr-1.5 h-3.5 w-3.5" aria-hidden />
              Letzten Report exportieren
            </Button>
          </div>

          {/* KPI Strip */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <KpiCard
              label="Prüfungen diesen Monat"
              value={KPIS.analysesThisMonth.value.toString()}
              delta={KPIS.analysesThisMonth.delta}
              deltaTone="positive"
              icon={Activity}
            />
            <KpiCard
              label="Ø Compliance-Score"
              value={`${KPIS.averageScore.value} %`}
              delta={KPIS.averageScore.delta}
              deltaTone="positive"
              icon={TrendingUp}
            />
            <KpiCard
              label="Verhinderte Risiko-Claims"
              value={KPIS.preventedRisks.value.toString()}
              sublabel={KPIS.preventedRisks.window}
              icon={ShieldCheck}
            />
          </div>

          {/* Editor + Result */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Editor Card */}
            <div className="flex flex-col rounded-xl border border-border/70 bg-card shadow-sm">
              <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
                <div className="flex items-center gap-1 rounded-md bg-muted/60 p-0.5">
                  {TABS.map((tab) => {
                    const Icon = tab.icon;
                    const active = activeTab === tab.id;
                    return (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => setActiveTab(tab.id)}
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors",
                          active
                            ? "bg-background text-foreground shadow-sm"
                            : "text-muted-foreground hover:text-foreground",
                        )}
                      >
                        <Icon className="h-3 w-3" aria-hidden />
                        {tab.label}
                      </button>
                    );
                  })}
                </div>

                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 rounded-md bg-muted/60 px-2 py-1 text-xs text-muted-foreground">
                    Lebensmittel / Supplement
                    <svg
                      viewBox="0 0 20 20"
                      className="h-3 w-3"
                      fill="currentColor"
                      aria-hidden
                    >
                      <path d="M5 8l5 5 5-5z" />
                    </svg>
                  </span>
                  <button
                    type="button"
                    aria-label="Optionen"
                    className="grid h-7 w-7 place-items-center rounded text-muted-foreground hover:bg-muted"
                  >
                    <MoreHorizontal className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </div>
              </div>

              <div className="flex-1 p-5">
                {activeTab === "text" && (
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    rows={9}
                    className="w-full resize-none border-0 bg-transparent font-serif text-[15px] leading-relaxed text-foreground outline-none placeholder:text-muted-foreground/70"
                    placeholder="Werbetext einfügen…"
                  />
                )}
                {activeTab === "url" && (
                  <div className="flex h-[180px] flex-col items-center justify-center gap-2 text-center">
                    <Link2 className="h-6 w-6 text-muted-foreground" aria-hidden />
                    <p className="text-sm text-muted-foreground">
                      URL einfügen, wir rendern die Seite und extrahieren den Text.
                    </p>
                  </div>
                )}
                {activeTab === "pdf" && (
                  <div className="flex h-[180px] flex-col items-center justify-center gap-2 text-center">
                    <Upload className="h-6 w-6 text-muted-foreground" aria-hidden />
                    <p className="text-sm text-muted-foreground">
                      PDF hier ablegen oder auswählen. Max. 10 MB.
                    </p>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between border-t border-border/60 px-4 py-3 text-xs text-muted-foreground">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span>{input.length} Zeichen</span>
                  <span className="inline-flex items-center gap-1">
                    <Sparkles className="h-3 w-3" aria-hidden />
                    ≈ 6 s Analyse
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Check className="h-3 w-3 text-primary" aria-hidden />
                    EU-Hosting aktiv
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" onClick={() => setInput("")}>
                    <RefreshCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                    Zurücksetzen
                  </Button>
                  <Button size="sm">
                    <Scan className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                    Claims prüfen
                  </Button>
                </div>
              </div>
            </div>

            {/* Result Panel (Empty State) */}
            <div className="flex flex-col rounded-xl border border-border/70 bg-card shadow-sm">
              <div className="border-b border-border/60 px-5 py-3">
                <h2 className="text-sm font-medium">Ergebnisse</h2>
              </div>
              <div className="flex flex-1 flex-col items-center justify-center gap-4 p-10 text-center">
                <span className="grid h-12 w-12 place-items-center rounded-full bg-accent text-accent-foreground">
                  <Sparkles className="h-5 w-5" aria-hidden />
                </span>
                <div>
                  <h3 className="font-serif text-lg font-semibold tracking-tight">
                    Bereit zur Analyse
                  </h3>
                  <p className="mt-1 max-w-xs text-sm text-muted-foreground">
                    Sobald du auf „Claims prüfen" klickst, identifiziert
                    ClaimGuard alle expliziten und impliziten Health Claims
                    und bewertet sie einzeln.
                  </p>
                </div>
                <div className="flex flex-wrap items-center justify-center gap-1.5">
                  <span className="inline-flex items-center gap-1 rounded-full bg-status-allowed-bg px-2 py-0.5 text-[11px] font-medium text-status-allowed">
                    <Check className="h-3 w-3" aria-hidden />
                    Konform
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-status-borderline-bg px-2 py-0.5 text-[11px] font-medium text-status-borderline">
                    <TriangleAlert className="h-3 w-3" aria-hidden />
                    Risiko
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-status-forbidden-bg px-2 py-0.5 text-[11px] font-medium text-status-forbidden">
                    <X className="h-3 w-3" aria-hidden />
                    Unzulässig
                  </span>
                </div>
              </div>
            </div>
          </div>

          <p className="max-w-3xl text-xs text-muted-foreground">
            ClaimGuard ist ein Assistenzsystem zur Compliance-Einschätzung und{" "}
            <strong className="font-semibold text-foreground">
              ersetzt keine Rechtsberatung
            </strong>
            . Im Zweifelsfall einen Fachanwalt für Wettbewerbsrecht konsultieren.
          </p>
        </div>
      </div>
    </>
  );
}
