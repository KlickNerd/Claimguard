"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
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
import {
  AnalysisProgress,
  PIPELINE_STEPS,
} from "@/components/app/analysis-progress";
import { ClaimCard } from "@/components/site/claim-card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { KPIS } from "@/lib/mock-analyses";
import { DEMO_CLAIMS, DEMO_INPUT } from "@/lib/demo-data";

const TABS = [
  { id: "text" as const, label: "Text", icon: FileText },
  { id: "url" as const, label: "URL", icon: Link2 },
  { id: "pdf" as const, label: "PDF", icon: Upload },
];

type Phase = "idle" | "running" | "done";

const STEP_DELAYS_MS = [500, 500, 1500, 1500, 2000];

export default function AppHomePage() {
  const [activeTab, setActiveTab] = useState<"text" | "url" | "pdf">("text");
  const [input, setInput] = useState(DEMO_INPUT);
  const [phase, setPhase] = useState<Phase>("idle");
  const [currentStep, setCurrentStep] = useState(0);
  const [evaluated, setEvaluated] = useState(0);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(
    () => () => {
      timers.current.forEach(clearTimeout);
    },
    [],
  );

  const runAnalysis = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setPhase("running");
    setCurrentStep(0);
    setEvaluated(0);

    let cumulative = 0;
    for (let i = 0; i < STEP_DELAYS_MS.length; i++) {
      cumulative += STEP_DELAYS_MS[i];
      timers.current.push(
        setTimeout(() => setCurrentStep(i + 1), cumulative),
      );
    }

    // Animate evaluated counter during evaluate step
    const beforeEvaluate = STEP_DELAYS_MS.slice(0, 4).reduce((a, b) => a + b, 0);
    DEMO_CLAIMS.forEach((_, i) => {
      timers.current.push(
        setTimeout(
          () => setEvaluated(i + 1),
          beforeEvaluate +
            ((i + 1) * STEP_DELAYS_MS[4]) / DEMO_CLAIMS.length,
        ),
      );
    });

    timers.current.push(setTimeout(() => setPhase("done"), cumulative + 200));
  };

  const resetAnalysis = () => {
    timers.current.forEach(clearTimeout);
    setPhase("idle");
    setCurrentStep(0);
    setEvaluated(0);
  };

  const runDisabled = input.trim().length < 50;

  return (
    <>
      <AppHeader
        crumbs={[{ label: "Workspace" }, { label: "Neue Prüfung" }]}
      />

      <div className="flex-1 px-6 py-8 lg:px-10">
        <div className="flex flex-col gap-8">
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
            <Button variant="outline" size="sm" asChild>
              <Link href="/app/history/chk_2k9f3a">
                <Download className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                Letzten Report ansehen
              </Link>
            </Button>
          </div>

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
                        disabled={phase === "running"}
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors",
                          active
                            ? "bg-background text-foreground shadow-sm"
                            : "text-muted-foreground hover:text-foreground",
                          phase === "running" && "cursor-not-allowed opacity-60",
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
                    disabled={phase === "running"}
                    rows={9}
                    className="w-full resize-none border-0 bg-transparent font-serif text-[15px] leading-relaxed text-foreground outline-none placeholder:text-muted-foreground/70 disabled:opacity-70"
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
                  <div className="flex h-[180px] flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border/70 text-center">
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
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={resetAnalysis}
                    disabled={phase === "running"}
                  >
                    <RefreshCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                    Zurücksetzen
                  </Button>
                  <Button
                    size="sm"
                    onClick={runAnalysis}
                    disabled={runDisabled || phase === "running"}
                  >
                    <Scan className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                    Claims prüfen
                  </Button>
                </div>
              </div>
            </div>

            {/* Result Panel */}
            <div className="flex flex-col rounded-xl border border-border/70 bg-card shadow-sm">
              <div className="flex items-center justify-between border-b border-border/60 px-5 py-3">
                <h2 className="text-sm font-medium">Ergebnisse</h2>
                {phase === "done" && (
                  <span className="font-mono text-[11px] text-muted-foreground">
                    Demo · nicht gespeichert
                  </span>
                )}
              </div>

              {phase === "idle" && <IdleState />}

              {phase === "running" && (
                <div className="flex flex-1 flex-col gap-6 p-6">
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Analyse läuft
                    </div>
                    <div className="mt-1 font-serif text-lg font-semibold tracking-tight">
                      Schritt {Math.min(currentStep + 1, PIPELINE_STEPS.length)} von{" "}
                      {PIPELINE_STEPS.length}
                    </div>
                  </div>
                  <AnalysisProgress
                    currentStep={currentStep}
                    claimsFound={currentStep >= 3 ? DEMO_CLAIMS.length : undefined}
                    claimsEvaluated={evaluated}
                  />
                </div>
              )}

              {phase === "done" && (
                <div className="flex-1 space-y-3 p-5">
                  {DEMO_CLAIMS.map((c) => (
                    <ClaimCard key={c.id} claim={c} />
                  ))}
                  <div className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                    <span>3 Claims bewertet · Demo-Daten</span>
                    <Button variant="ghost" size="sm" onClick={resetAnalysis}>
                      <RefreshCcw className="mr-1.5 h-3 w-3" aria-hidden />
                      Neu prüfen
                    </Button>
                  </div>
                </div>
              )}
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

function IdleState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-10 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-full bg-accent text-accent-foreground">
        <Sparkles className="h-5 w-5" aria-hidden />
      </span>
      <div>
        <h3 className="font-serif text-lg font-semibold tracking-tight">
          Bereit zur Analyse
        </h3>
        <p className="mt-1 max-w-xs text-sm text-muted-foreground">
          Sobald du auf „Claims prüfen" klickst, identifiziert ClaimGuard alle
          expliziten und impliziten Health Claims und bewertet sie einzeln.
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
  );
}
