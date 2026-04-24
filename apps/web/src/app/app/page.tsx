"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  Check,
  Download,
  FileText,
  Info,
  Link2,
  MoreHorizontal,
  RefreshCcw,
  Scan,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Upload,
} from "lucide-react";
import { AppHeader } from "@/components/app/app-header";
import { KpiCard } from "@/components/app/kpi-card";
import {
  AnalysisProgress,
  PIPELINE_STEPS,
} from "@/components/app/analysis-progress";
import { DetectionClaimCard } from "@/components/app/detection-claim-card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { KPIS } from "@/lib/mock-analyses";
import { DEMO_INPUT } from "@/lib/demo-data";
import {
  AnalysisError,
  createAnalysis,
  type AnalysisResponse,
} from "@/lib/api-client";

const TABS = [
  { id: "text" as const, label: "Text", icon: FileText },
  { id: "url" as const, label: "URL", icon: Link2 },
  { id: "pdf" as const, label: "PDF", icon: Upload },
];

type Phase = "idle" | "running" | "done" | "error";

// Animation hits step 3 (detect) after ~1s and holds there until the API
// response lands; final steps play out quickly once results arrive.
const STEP_DELAYS_MS = [500, 500, 500];

export default function AppHomePage() {
  const [activeTab, setActiveTab] = useState<"text" | "url" | "pdf">("text");
  const [input, setInput] = useState(DEMO_INPUT);
  const [phase, setPhase] = useState<Phase>("idle");
  const [currentStep, setCurrentStep] = useState(0);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(
    () => () => {
      timers.current.forEach(clearTimeout);
    },
    [],
  );

  const clearTimers = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };

  const runAnalysis = async () => {
    clearTimers();
    setPhase("running");
    setCurrentStep(0);
    setResult(null);
    setError(null);

    // Walk through steps 0→1→2 with delays so the user sees progression even
    // when the backend is quick. Step 3 (retrieve) + 4 (evaluate) are marked
    // as "übersprungen" once the detection-only API returns.
    let cumulative = 0;
    for (let i = 0; i < STEP_DELAYS_MS.length; i++) {
      cumulative += STEP_DELAYS_MS[i];
      timers.current.push(
        setTimeout(() => setCurrentStep(i + 1), cumulative),
      );
    }

    try {
      const response = await createAnalysis({ input_text: input });
      clearTimers();
      setCurrentStep(PIPELINE_STEPS.length);
      setResult(response);
      setPhase("done");
    } catch (err) {
      clearTimers();
      if (err instanceof AnalysisError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unbekannter Fehler bei der Analyse.");
      }
      setPhase("error");
    }
  };

  const resetAnalysis = () => {
    clearTimers();
    setPhase("idle");
    setCurrentStep(0);
    setResult(null);
    setError(null);
  };

  const runDisabled = input.trim().length < 50;

  const counts = result?.detected_claims.reduce(
    (acc, claim) => {
      acc[claim.claim_type] = (acc[claim.claim_type] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

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
                erkennt Health Claims und kategorisiert sie nach HCVO-Typ.
              </p>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link href="/app/history/chk_2k9f3a">
                <Download className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                Beispielreport ansehen
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
                      URL-Analyse folgt in einem nächsten Schritt.
                    </p>
                  </div>
                )}
                {activeTab === "pdf" && (
                  <div className="flex h-[180px] flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border/70 text-center">
                    <Upload className="h-6 w-6 text-muted-foreground" aria-hidden />
                    <p className="text-sm text-muted-foreground">
                      PDF-Upload folgt mit PROJ-12.
                    </p>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between border-t border-border/60 px-4 py-3 text-xs text-muted-foreground">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span>{input.length} Zeichen</span>
                  <span className="inline-flex items-center gap-1">
                    <Sparkles className="h-3 w-3" aria-hidden />
                    Sonnet 4.6
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Check className="h-3 w-3 text-primary" aria-hidden />
                    Zero-Retention
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
                {phase === "done" && result && (
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {result.latency_ms} ms · {result.input_tokens}/{result.output_tokens} Tokens
                  </span>
                )}
              </div>

              {phase === "idle" && <IdleState />}
              {phase === "running" && (
                <RunningState currentStep={currentStep} />
              )}
              {phase === "error" && (
                <ErrorState message={error} onReset={resetAnalysis} />
              )}
              {phase === "done" && result && (
                <DoneState
                  result={result}
                  counts={counts ?? {}}
                  onReset={resetAnalysis}
                />
              )}
            </div>
          </div>

          <p className="max-w-3xl text-xs text-muted-foreground">
            Stand {new Date().toLocaleDateString("de-DE")}: Detection läuft live gegen
            Claude Sonnet 4.6. Rechtliche Bewertung (Konform / Risiko / Unzulässig) und
            Reformulierung folgen, sobald Retrieval (PROJ-9) und Evaluation (PROJ-10)
            verdrahtet sind.
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
          Klick „Claims prüfen" – Sonnet 4.6 erkennt alle expliziten und
          impliziten Health Claims im Text.
        </p>
      </div>
    </div>
  );
}

function RunningState({ currentStep }: { currentStep: number }) {
  return (
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
      <AnalysisProgress currentStep={currentStep} />
      <p className="mt-auto text-[11px] text-muted-foreground">
        Sonnet 4.6 braucht in der Regel 2–6 Sekunden pro Analyse.
      </p>
    </div>
  );
}

function ErrorState({
  message,
  onReset,
}: {
  message: string | null;
  onReset: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-full bg-status-forbidden-bg text-status-forbidden">
        <AlertCircle className="h-5 w-5" aria-hidden />
      </span>
      <div>
        <h3 className="font-serif text-lg font-semibold tracking-tight">
          Analyse fehlgeschlagen
        </h3>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          {message ?? "Unbekannter Fehler."}
        </p>
      </div>
      <Button variant="outline" size="sm" onClick={onReset}>
        <RefreshCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden />
        Erneut versuchen
      </Button>
    </div>
  );
}

function DoneState({
  result,
  counts,
  onReset,
}: {
  result: AnalysisResponse;
  counts: Record<string, number>;
  onReset: () => void;
}) {
  const claimCount = result.detected_claims.length;
  const disease = counts.disease_based ?? 0;
  return (
    <div className="flex-1 space-y-3 p-5">
      {claimCount === 0 ? (
        <div className="rounded-lg border border-border/60 bg-muted/40 p-4 text-sm text-muted-foreground">
          {result.warnings[0] ??
            "Keine gesundheitsbezogenen Aussagen gefunden."}
        </div>
      ) : (
        <>
          <div className="flex items-start gap-3 rounded-lg border border-accent/60 bg-accent/40 p-3 text-xs">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-foreground" aria-hidden />
            <p className="text-foreground/80">
              <strong className="font-semibold">{claimCount} Claims erkannt.</strong>{" "}
              Rechtliche Bewertung folgt in Stufe 3 – zeigt dann Status, Rechtsgrundlage und
              Reformulierung.{" "}
              {disease > 0 && (
                <span className="text-status-forbidden">
                  {disease} krankheitsbezogene Aussage(n) – hohes Abmahn-Risiko.
                </span>
              )}
            </p>
          </div>
          {result.detected_claims.map((claim) => (
            <DetectionClaimCard key={claim.id} claim={claim} />
          ))}
        </>
      )}
      {result.warnings.length > 0 && claimCount > 0 && (
        <div className="rounded-lg border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground">
          {result.warnings.map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}
      <div className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
        <span>
          {result.model} · {result.latency_ms} ms
        </span>
        <Button variant="ghost" size="sm" onClick={onReset}>
          <RefreshCcw className="mr-1.5 h-3 w-3" aria-hidden />
          Neu prüfen
        </Button>
      </div>
    </div>
  );
}
