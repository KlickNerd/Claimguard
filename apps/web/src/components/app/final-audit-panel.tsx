"use client";

import {
  AlertCircle,
  AlertTriangle,
  Check,
  CheckCircle2,
  Loader2,
  ShieldCheck,
  Sparkles,
  Wand2,
} from "lucide-react";

import type {
  AuditCategory,
  AuditFinding,
  AuditSeverity,
  FinalAuditResult,
} from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Props = {
  result: FinalAuditResult | null;
  isAuditing: boolean;
  error: string | null;
  onRun: () => void;
  onReset?: () => void;
  // Apply a single finding's replacement to the current text. The
  // index identifies the finding in result.findings.
  onApplyFinding?: (index: number) => void;
  // Apply all findings that have a non-null replacement and a severity
  // of "critical" or "high". Default behavior is "fix the urgent stuff
  // in one click, leave low/medium for review".
  onApplyAllCriticalHigh?: () => void;
  // Set of finding indices that have already been applied. Renders
  // those as "Übernommen" with a strikethrough on the location quote.
  appliedFindings?: Set<number>;
  // Trigger the "one-shot LLM rewrite" of the entire text per audit
  // findings. Distinct from the deterministic per-finding apply: this
  // is a single Sonnet call that returns a fully rewritten text.
  onApplyAllByLLM?: () => void;
  isApplyingAllByLLM?: boolean;
  applyAllByLLMError?: string | null;
};

const SEVERITY_TONE: Record<AuditSeverity, { bg: string; fg: string; label: string }> = {
  critical: {
    bg: "bg-status-forbidden-bg",
    fg: "text-status-forbidden",
    label: "Kritisch",
  },
  high: {
    bg: "bg-status-forbidden-bg",
    fg: "text-status-forbidden",
    label: "Hoch",
  },
  medium: {
    bg: "bg-status-borderline-bg",
    fg: "text-status-borderline",
    label: "Mittel",
  },
  low: {
    bg: "bg-status-unclear-bg",
    fg: "text-status-unclear",
    label: "Niedrig",
  },
};

const CATEGORY_LABELS: Record<AuditCategory, string> = {
  "broken-table": "Kaputte Tabelle",
  "broken-list": "Kaputte Liste",
  "duplicate-paragraph": "Duplikat-Absatz",
  "orphaned-sentence": "Verwaister Satz",
  "topic-drift": "Topic-Drift",
  "answer-misses-question": "Antwort verfehlt Frage",
  "factual-error": "Sachfehler",
  "circular-content": "Zirkulärer Inhalt",
  "implicit-claim-by-context": "Impliziter Claim (Kontext)",
  "context-disease-link": "Kontext-Krankheitsbezug",
  "uwg-comparative": "UWG § 6 – vergleichend",
  "uwg-misleading": "UWG § 5 – Irreführung",
  "hwg-violation": "HWG-Verstoß",
  "lazy-disclaimer": "Lazy-Disclaimer",
  other: "Sonstiges",
};

export function FinalAuditPanel({
  result,
  isAuditing,
  error,
  onRun,
  onReset,
  onApplyFinding,
  onApplyAllCriticalHigh,
  appliedFindings,
  onApplyAllByLLM,
  isApplyingAllByLLM,
  applyAllByLLMError,
}: Props) {
  // Empty initial state - render the "trigger" card so the user knows
  // the audit exists.
  if (!result && !isAuditing && !error) {
    return (
      <div className="rounded-xl border border-border/70 bg-card p-5">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-primary/10 text-primary">
            <Sparkles className="h-4 w-4" aria-hidden />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold">
              Finaler Compliance-Check (Opus 4.7)
            </h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Holistischer Review über den gesamten Text. Findet, was die
              Claim-für-Claim-Analyse strukturell nicht sehen kann:
              kaputte Tabellen, Topic-Drift in FAQs, doppelte Absätze,
              Sachfehler, UWG-/HWG-Risiken, Kontext-Claims.
            </p>
            <Button
              type="button"
              size="sm"
              variant="default"
              className="mt-3"
              onClick={onRun}
              disabled={isAuditing}
            >
              <ShieldCheck className="mr-1.5 h-3.5 w-3.5" aria-hidden />
              Jetzt prüfen
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (isAuditing) {
    return (
      <div className="flex items-center gap-3 rounded-xl border border-border/70 bg-card p-5 text-sm">
        <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden />
        <span>
          Finaler Compliance-Check läuft (Opus 4.7) — kann 30–60 Sekunden dauern …
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-status-forbidden/30 bg-status-forbidden-bg/40 p-5">
        <div className="flex items-start gap-3">
          <AlertCircle
            className="mt-0.5 h-4 w-4 shrink-0 text-status-forbidden"
            aria-hidden
          />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-status-forbidden">
              Compliance-Check fehlgeschlagen
            </h3>
            <p className="mt-1 text-xs text-muted-foreground">{error}</p>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="mt-3"
              onClick={onRun}
            >
              Noch einmal versuchen
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!result) return null;

  // Track findings by their *original* index in result.findings, so the
  // per-finding apply-handler hits the right one even after severity
  // grouping. We keep an "indexed" list inline so the inner map can
  // emit `originalIndex` cleanly.
  type IndexedFinding = { finding: AuditFinding; originalIndex: number };
  const indexed: IndexedFinding[] = result.findings.map((finding, i) => ({
    finding,
    originalIndex: i,
  }));

  const findingsBySeverity = indexed.reduce<
    Record<AuditSeverity, IndexedFinding[]>
  >(
    (acc, item) => {
      acc[item.finding.severity].push(item);
      return acc;
    },
    { critical: [], high: [], medium: [], low: [] },
  );

  // Count: how many critical+high findings still have an applicable
  // replacement and haven't been applied yet. Drives the "Alle
  // anwenden"-button visibility.
  const applicableUrgent = indexed.filter(
    ({ finding, originalIndex }) =>
      (finding.severity === "critical" || finding.severity === "high") &&
      typeof finding.replacement === "string" &&
      !appliedFindings?.has(originalIndex),
  ).length;

  return (
    <div className="space-y-3">
      <div
        className={cn(
          "rounded-xl border p-5",
          result.shippable
            ? "border-status-allowed/30 bg-status-allowed-bg/40"
            : "border-status-borderline/40 bg-status-borderline-bg/40",
        )}
      >
        <div className="flex items-start gap-3">
          {result.shippable ? (
            <CheckCircle2
              className="mt-0.5 h-5 w-5 shrink-0 text-status-allowed"
              aria-hidden
            />
          ) : (
            <AlertTriangle
              className="mt-0.5 h-5 w-5 shrink-0 text-status-borderline"
              aria-hidden
            />
          )}
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold">
                Finaler Compliance-Check
              </h3>
              <span
                className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
                  result.shippable
                    ? "bg-status-allowed-bg text-status-allowed"
                    : "bg-status-borderline-bg text-status-borderline",
                )}
              >
                {result.shippable ? "Versandbereit" : "Nacharbeit nötig"}
              </span>
            </div>
            <p className="mt-1.5 text-sm text-foreground/90">
              {result.overall_assessment}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
              <span>{result.findings.length} Findings</span>
              <span>·</span>
              <span>{result.model}</span>
              <span>·</span>
              <span>{(result.latency_ms / 1000).toFixed(1)} s</span>
              {onReset && result.findings.length > 0 ? (
                <>
                  <span>·</span>
                  <button
                    type="button"
                    onClick={onReset}
                    className="underline-offset-4 hover:underline"
                  >
                    Schließen
                  </button>
                </>
              ) : null}
            </div>
            {!result.shippable && onApplyAllByLLM && (
              <div className="mt-3">
                <Button
                  type="button"
                  size="sm"
                  variant="default"
                  onClick={onApplyAllByLLM}
                  disabled={isApplyingAllByLLM}
                  className="bg-primary"
                >
                  {isApplyingAllByLLM ? (
                    <>
                      <Loader2
                        className="mr-1.5 h-3.5 w-3.5 animate-spin"
                        aria-hidden
                      />
                      Claude wendet die Befunde an …
                    </>
                  ) : (
                    <>
                      <Wand2 className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                      Audit-Befunde komplett umsetzen lassen
                    </>
                  )}
                </Button>
                {applyAllByLLMError ? (
                  <p className="mt-1.5 text-[11px] text-status-forbidden">
                    {applyAllByLLMError}
                  </p>
                ) : null}
                <p className="mt-1.5 text-[11px] text-muted-foreground">
                  Sonnet 4.6 überarbeitet den Text in einem Durchgang.
                  {result.findings.length === 0
                    ? " Da keine strukturierten Findings vorliegen, "
                      + "nutzt Sonnet die Executive Summary als Anweisung."
                    : ` Adressiert alle ${result.findings.length} Findings oben.`}
                </p>
              </div>
            )}

            {applicableUrgent > 0 && onApplyAllCriticalHigh && (
              <div className="mt-2">
                <button
                  type="button"
                  onClick={onApplyAllCriticalHigh}
                  className="inline-flex items-center gap-1 rounded text-[11px] font-medium text-muted-foreground transition-colors hover:text-foreground"
                >
                  <Check className="h-3 w-3" aria-hidden />
                  Stattdessen nur die {applicableUrgent} kritischen/hohen
                  Findings deterministisch übernehmen
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {(["critical", "high", "medium", "low"] as AuditSeverity[]).map(
        (sev) => {
          const items = findingsBySeverity[sev];
          if (!items || items.length === 0) return null;
          const tone = SEVERITY_TONE[sev];
          return (
            <div key={sev} className="space-y-2">
              <div className="flex items-center gap-2 px-1">
                <span
                  className={cn(
                    "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
                    tone.bg,
                    tone.fg,
                  )}
                >
                  {tone.label}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {items.length} {items.length === 1 ? "Finding" : "Findings"}
                </span>
              </div>
              {items.map(({ finding, originalIndex }) => (
                <FindingCard
                  key={`${sev}-${originalIndex}`}
                  finding={finding}
                  isApplied={appliedFindings?.has(originalIndex) ?? false}
                  onApply={
                    onApplyFinding
                      ? () => onApplyFinding(originalIndex)
                      : undefined
                  }
                />
              ))}
            </div>
          );
        },
      )}
    </div>
  );
}

function FindingCard({
  finding,
  isApplied,
  onApply,
}: {
  finding: AuditFinding;
  isApplied: boolean;
  onApply?: () => void;
}) {
  const tone = SEVERITY_TONE[finding.severity];
  const canApply = !isApplied && typeof finding.replacement === "string";
  const willDelete = finding.replacement === "";
  return (
    <div
      className={cn(
        "rounded-xl border border-border/70 bg-card p-4",
        isApplied && "border-status-allowed/50 bg-status-allowed-bg/30",
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
              tone.bg,
              tone.fg,
            )}
          >
            {tone.label}
          </span>
          <span className="text-[11px] font-medium text-muted-foreground">
            {CATEGORY_LABELS[finding.category]}
          </span>
          {isApplied && (
            <span className="inline-flex items-center gap-1 rounded-full bg-status-allowed-bg px-2 py-0.5 text-[10px] font-medium text-status-allowed">
              <Check className="h-2.5 w-2.5" aria-hidden />
              Übernommen
            </span>
          )}
        </div>
        {canApply && onApply ? (
          <button
            type="button"
            onClick={onApply}
            className="inline-flex items-center gap-1 rounded bg-primary px-2 py-1 text-[11px] font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            {willDelete ? (
              <>Streichen</>
            ) : (
              <>
                <Check className="h-3 w-3" aria-hidden />
                Übernehmen
              </>
            )}
          </button>
        ) : null}
      </div>
      <blockquote
        className={cn(
          "mt-2 rounded-md bg-muted/40 px-3 py-2 text-xs italic text-foreground/80",
          isApplied && "line-through opacity-60",
        )}
      >
        „{finding.location_quote}"
      </blockquote>
      <p className="mt-2.5 text-sm leading-relaxed text-foreground/90">
        {finding.finding}
      </p>
      <div className="mt-2 rounded-md border-l-2 border-primary/40 bg-primary/5 px-3 py-2">
        <div className="text-[10px] font-semibold uppercase tracking-wide text-primary">
          Empfehlung
        </div>
        <p className="mt-0.5 text-xs leading-relaxed text-foreground/85">
          {finding.recommendation}
        </p>
      </div>
      {typeof finding.replacement === "string" && finding.replacement !== "" && (
        <div className="mt-2 rounded-md border border-status-allowed/30 bg-status-allowed-bg/30 px-3 py-2">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-status-allowed">
            Konkreter Ersetzungs-Text
          </div>
          <p className="mt-0.5 whitespace-pre-wrap text-xs leading-relaxed text-foreground/90">
            {finding.replacement}
          </p>
        </div>
      )}
      {finding.replacement === null && (
        <div className="mt-2 rounded-md border border-status-borderline/30 bg-status-borderline-bg/30 px-3 py-2">
          <p className="text-xs leading-relaxed text-foreground/75">
            Diese Stelle muss manuell überarbeitet werden — kein
            automatischer Ersetzungs-Vorschlag verfügbar.
          </p>
        </div>
      )}
    </div>
  );
}
