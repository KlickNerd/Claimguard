"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertCircle,
  Check,
  CheckCheck,
  Clipboard,
  Download,
  FileText,
  Info,
  Link2,
  MoreHorizontal,
  Pencil,
  RefreshCcw,
  RotateCcw,
  Scan,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  TriangleAlert,
  Upload,
} from "lucide-react";
import { AppHeader } from "@/components/app/app-header";
import { KpiCard } from "@/components/app/kpi-card";
import {
  AnalysisProgress,
  PIPELINE_STEPS,
} from "@/components/app/analysis-progress";
import { DetectionClaimCard } from "@/components/app/detection-claim-card";
import { EvaluatedClaimCard } from "@/components/app/evaluated-claim-card";
import { HighlightedText } from "@/components/app/highlighted-text";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { KPIS } from "@/lib/mock-analyses";
import { DEMO_INPUT } from "@/lib/demo-data";
import {
  AnalysisError,
  createAnalysis,
  type AnalysisResponse,
  type EvaluatedClaim,
} from "@/lib/api-client";

const TABS = [
  { id: "text" as const, label: "Text", icon: FileText },
  { id: "url" as const, label: "URL", icon: Link2 },
  { id: "pdf" as const, label: "PDF", icon: Upload },
];

type Phase = "idle" | "running" | "done" | "error";

const STEP_DELAYS_MS = [500, 500, 500];

const MIN_CHARS = 50;
const MAX_CHARS = 50_000;
const WARN_THRESHOLD = 0.9;

/**
 * Apply rewrites in descending position order so earlier claims keep their
 * original positions while we patch the text. Returns the rewritten string.
 */
function applyRewritesToText(
  originalText: string,
  evaluatedClaims: EvaluatedClaim[],
  appliedIds: Set<string>,
): string {
  const ordered = evaluatedClaims
    .filter((c) => appliedIds.has(c.id) && c.rewrite_suggestion)
    .sort((a, b) => b.position_start - a.position_start);

  let text = originalText;
  for (const claim of ordered) {
    text =
      text.slice(0, claim.position_start) +
      (claim.rewrite_suggestion ?? "") +
      text.slice(claim.position_end);
  }
  return text;
}

export default function AppHomePage() {
  const [activeTab, setActiveTab] = useState<"text" | "url" | "pdf">("text");
  const [input, setInput] = useState(DEMO_INPUT);
  const [phase, setPhase] = useState<Phase>("idle");
  const [currentStep, setCurrentStep] = useState(0);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeClaimId, setActiveClaimId] = useState<string | null>(null);
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());
  const [copyHint, setCopyHint] = useState(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const editorRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    const el = editorRef.current;
    if (!el) return;
    el.style.height = "auto";
    const next = Math.min(Math.max(el.scrollHeight, 240), 720);
    el.style.height = `${next}px`;
  }, [input, phase]);

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

  const runAnalysis = async (overrideInput?: string) => {
    const text = overrideInput ?? input;
    clearTimers();
    setPhase("running");
    setCurrentStep(0);
    setResult(null);
    setError(null);
    setAppliedIds(new Set());

    let cumulative = 0;
    for (let i = 0; i < STEP_DELAYS_MS.length; i++) {
      cumulative += STEP_DELAYS_MS[i];
      timers.current.push(
        setTimeout(() => setCurrentStep(i + 1), cumulative),
      );
    }

    try {
      const response = await createAnalysis({ input_text: text });
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
    setActiveClaimId(null);
    setAppliedIds(new Set());
  };

  const length = input.length;
  const tooShort = input.trim().length < MIN_CHARS;
  const tooLong = length > MAX_CHARS;
  const warnLength = length >= MAX_CHARS * WARN_THRESHOLD && !tooLong;
  const runDisabled = tooShort || tooLong;

  const counts = useMemo(() => {
    if (!result) return null;
    const evals = result.evaluated_claims;
    return {
      total: result.detected_claims.length,
      evaluated: evals.length,
      allowed: evals.filter((c) => c.status === "allowed").length,
      borderline: evals.filter((c) => c.status === "borderline").length,
      forbidden: evals.filter((c) => c.status === "forbidden").length,
      unclear: evals.filter((c) => c.status === "unclear").length,
    };
  }, [result]);

  const applicableClaims = useMemo(() => {
    if (!result) return [];
    return result.evaluated_claims.filter(
      (c) =>
        c.rewrite_suggestion &&
        (c.status === "borderline" || c.status === "forbidden"),
    );
  }, [result]);

  const editedText = useMemo(() => {
    if (!result || appliedIds.size === 0) return null;
    return applyRewritesToText(
      result.input_text,
      result.evaluated_claims,
      appliedIds,
    );
  }, [result, appliedIds]);

  const handleClaimClick = (claimId: string) => {
    setActiveClaimId(claimId);
    const el = document.getElementById(`claim-${claimId}`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const applyClaim = (claimId: string) => {
    setAppliedIds((prev) => new Set(prev).add(claimId));
    setActiveClaimId(claimId);
  };

  const revertClaim = (claimId: string) => {
    setAppliedIds((prev) => {
      const next = new Set(prev);
      next.delete(claimId);
      return next;
    });
  };

  const applyAll = () => {
    setAppliedIds(new Set(applicableClaims.map((c) => c.id)));
  };

  const revertAll = () => {
    setAppliedIds(new Set());
  };

  const copyEditedText = async () => {
    const text = editedText ?? result?.input_text;
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopyHint(true);
    window.setTimeout(() => setCopyHint(false), 2000);
  };

  const recheckEditedText = () => {
    if (!editedText) return;
    setInput(editedText);
    void runAnalysis(editedText);
  };

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
                erkennt und bewertet jeden Health Claim.
              </p>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link href="/app/history/chk_2k9f3a">
                <Download className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                Beispielreport
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
            {/* LEFT: Editor or HighlightedText */}
            <div className="flex flex-col rounded-xl border border-border/70 bg-card shadow-sm">
              <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
                <div className="flex items-center gap-1 rounded-md bg-muted/60 p-0.5">
                  {TABS.map((tab) => {
                    const Icon = tab.icon;
                    const active = activeTab === tab.id;
                    const disabled =
                      phase === "running" || phase === "done";
                    return (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => setActiveTab(tab.id)}
                        disabled={disabled}
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors",
                          active
                            ? "bg-background text-foreground shadow-sm"
                            : "text-muted-foreground hover:text-foreground",
                          disabled && "cursor-not-allowed opacity-60",
                        )}
                      >
                        <Icon className="h-3 w-3" aria-hidden />
                        {tab.label}
                      </button>
                    );
                  })}
                </div>

                <div className="flex items-center gap-2">
                  {phase === "done" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={resetAnalysis}
                      className="h-7 px-2 text-xs"
                    >
                      <Pencil className="mr-1 h-3 w-3" aria-hidden />
                      Bearbeiten
                    </Button>
                  )}
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

              {phase === "done" && result ? (
                editedText ? (
                  <EditedTextView
                    text={editedText}
                    appliedCount={appliedIds.size}
                  />
                ) : (
                  <HighlightedText
                    text={result.input_text}
                    detectedClaims={result.detected_claims}
                    evaluatedClaims={result.evaluated_claims}
                    onClaimClick={handleClaimClick}
                    activeClaimId={activeClaimId}
                  />
                )
              ) : (
                <>
                  {activeTab === "text" && (
                    <div className="flex-1 p-5">
                      <textarea
                        ref={editorRef}
                        value={input}
                        onChange={(e) =>
                          setInput(e.target.value.slice(0, MAX_CHARS))
                        }
                        disabled={phase === "running"}
                        maxLength={MAX_CHARS}
                        className="block min-h-[240px] w-full resize-none border-0 bg-transparent font-serif text-[15px] leading-relaxed text-foreground outline-none placeholder:text-muted-foreground/70 disabled:opacity-70"
                        placeholder="Werbetext einfügen…"
                      />
                    </div>
                  )}
                  {activeTab === "url" && (
                    <div className="flex h-[240px] flex-col items-center justify-center gap-2 text-center">
                      <Link2 className="h-6 w-6 text-muted-foreground" aria-hidden />
                      <p className="text-sm text-muted-foreground">
                        URL-Analyse folgt in einem nächsten Schritt.
                      </p>
                    </div>
                  )}
                  {activeTab === "pdf" && (
                    <div className="flex h-[240px] flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border/70 text-center">
                      <Upload className="h-6 w-6 text-muted-foreground" aria-hidden />
                      <p className="text-sm text-muted-foreground">
                        PDF-Upload folgt mit PROJ-12.
                      </p>
                    </div>
                  )}
                </>
              )}

              <div className="flex items-center justify-between border-t border-border/60 px-4 py-3 text-xs text-muted-foreground">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 tabular-nums",
                      warnLength && "text-status-borderline",
                      tooLong && "font-semibold text-status-forbidden",
                    )}
                  >
                    {warnLength && (
                      <TriangleAlert className="h-3 w-3" aria-hidden />
                    )}
                    {(editedText ?? input).length.toLocaleString("de-DE")} /{" "}
                    {MAX_CHARS.toLocaleString("de-DE")} Zeichen
                  </span>
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
                  {phase === "done" && editedText ? (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={copyEditedText}
                      >
                        <Clipboard className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                        {copyHint ? "Kopiert!" : "Text kopieren"}
                      </Button>
                      <Button size="sm" onClick={recheckEditedText}>
                        <RefreshCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                        Erneut prüfen
                      </Button>
                    </>
                  ) : (
                    <>
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
                        onClick={() => runAnalysis()}
                        disabled={runDisabled || phase === "running" || phase === "done"}
                      >
                        <Scan className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                        Claims prüfen
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* RIGHT: Result panel */}
            <div className="flex flex-col rounded-xl border border-border/70 bg-card shadow-sm">
              <div className="flex items-center justify-between border-b border-border/60 px-5 py-3">
                <h2 className="text-sm font-medium">Ergebnisse</h2>
                {phase === "done" && result && (
                  <span className="font-mono text-[11px] text-muted-foreground">
                    {(result.latency_ms / 1000).toFixed(1)} s · {result.input_tokens}/{result.output_tokens} Tokens
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
              {phase === "done" && result && counts && (
                <DoneState
                  result={result}
                  counts={counts}
                  applicableClaims={applicableClaims}
                  appliedIds={appliedIds}
                  activeClaimId={activeClaimId}
                  onSelectClaim={handleClaimClick}
                  onApplyClaim={applyClaim}
                  onRevertClaim={revertClaim}
                  onApplyAll={applyAll}
                  onRevertAll={revertAll}
                />
              )}
            </div>
          </div>

          <p className="max-w-3xl text-xs text-muted-foreground">
            <strong className="font-semibold text-foreground">Stufe 2 (KI-Schätzung):</strong>{" "}
            Detection und Bewertung laufen live gegen Claude Sonnet 4.6. Die genannten
            Rechtsgrundlagen sind <strong>nicht aus einer kuratierten Quellen-Datenbank</strong>{" "}
            zitiert – Aktenzeichen sollten gegengeprüft werden. Mit Stufe 3 (PROJ-9 Retrieval +
            PROJ-10 Opus-Evaluation) folgen verifizierte Zitate.
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
          Klick „Claims prüfen" – Sonnet 4.6 erkennt und bewertet alle Health
          Claims im Text.
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
        Detection in 2-6 s, Bewertung läuft parallel pro Claim.
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

function EditedTextView({
  text,
  appliedCount,
}: {
  text: string;
  appliedCount: number;
}) {
  return (
    <div className="overflow-y-auto px-5 py-5">
      <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-status-allowed-bg px-2.5 py-1 text-[11px] font-medium text-status-allowed">
        <CheckCheck className="h-3 w-3" aria-hidden />
        {appliedCount} Reformulierung
        {appliedCount > 1 ? "en" : ""} übernommen – bearbeitete Version
      </div>
      <p className="whitespace-pre-wrap font-serif text-[15px] leading-[1.85] text-foreground">
        {text}
      </p>
    </div>
  );
}

function DoneState({
  result,
  counts,
  applicableClaims,
  appliedIds,
  activeClaimId,
  onSelectClaim,
  onApplyClaim,
  onRevertClaim,
  onApplyAll,
  onRevertAll,
}: {
  result: AnalysisResponse;
  counts: {
    total: number;
    evaluated: number;
    allowed: number;
    borderline: number;
    forbidden: number;
    unclear: number;
  };
  applicableClaims: EvaluatedClaim[];
  appliedIds: Set<string>;
  activeClaimId: string | null;
  onSelectClaim: (id: string) => void;
  onApplyClaim: (id: string) => void;
  onRevertClaim: (id: string) => void;
  onApplyAll: () => void;
  onRevertAll: () => void;
}) {
  const detectedNotEvaluated = result.detected_claims.filter(
    (d) => !result.evaluated_claims.some((e) => e.id === d.id),
  );
  const totalApplicable = applicableClaims.length;
  const allApplied = totalApplicable > 0 && appliedIds.size === totalApplicable;

  return (
    <div className="flex-1 space-y-3 overflow-y-auto p-5">
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-accent/50 bg-accent/30 px-3 py-2 text-xs">
        <Info className="h-3.5 w-3.5 shrink-0 text-accent-foreground" aria-hidden />
        <span className="text-foreground/85">
          <strong className="font-semibold">{counts.total} Claims erkannt,</strong>{" "}
          {counts.evaluated} bewertet
          {counts.evaluated > 0 && (
            <>
              {" "}
              · <span className="text-status-allowed">{counts.allowed} konform</span>
              {" / "}
              <span className="text-status-borderline">{counts.borderline} Risiko</span>
              {" / "}
              <span className="text-status-forbidden">{counts.forbidden} unzulässig</span>
              {counts.unclear > 0 && (
                <>
                  {" / "}
                  <span className="text-status-unclear">{counts.unclear} unklar</span>
                </>
              )}
            </>
          )}
        </span>
      </div>

      {totalApplicable > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-xs">
          <span className="text-foreground/85">
            <strong className="font-semibold tabular-nums">
              {appliedIds.size} / {totalApplicable}
            </strong>{" "}
            Reformulierungen übernommen
          </span>
          <div className="flex items-center gap-1.5">
            {appliedIds.size > 0 && (
              <button
                type="button"
                onClick={onRevertAll}
                className="inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                <RotateCcw className="h-3 w-3" aria-hidden />
                Alle zurücksetzen
              </button>
            )}
            {!allApplied && (
              <button
                type="button"
                onClick={onApplyAll}
                className="inline-flex items-center gap-1 rounded bg-primary px-2.5 py-1 text-[11px] font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
              >
                <CheckCheck className="h-3 w-3" aria-hidden />
                Alle übernehmen
              </button>
            )}
          </div>
        </div>
      )}

      {result.evaluated_claims.map((claim, i) => (
        <EvaluatedClaimCard
          key={claim.id}
          claim={claim}
          index={i + 1}
          isActive={activeClaimId === claim.id}
          isApplied={appliedIds.has(claim.id)}
          onSelect={() => onSelectClaim(claim.id)}
          onApply={
            claim.rewrite_suggestion &&
            (claim.status === "borderline" || claim.status === "forbidden")
              ? () => onApplyClaim(claim.id)
              : undefined
          }
          onRevert={() => onRevertClaim(claim.id)}
        />
      ))}

      {detectedNotEvaluated.length > 0 && (
        <div className="space-y-3">
          <div className="rounded-lg border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground">
            {detectedNotEvaluated.length} Claim(s) wurden erkannt, aber nicht
            bewertet – Schema-Fehler bei der Bewertung. Detection-Daten:
          </div>
          {detectedNotEvaluated.map((claim) => (
            <DetectionClaimCard key={claim.id} claim={claim} />
          ))}
        </div>
      )}

      {result.warnings.map((w, i) => (
        <div
          key={i}
          className="rounded-lg border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground"
        >
          {w}
        </div>
      ))}
    </div>
  );
}
