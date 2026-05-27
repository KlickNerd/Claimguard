"use client";

import { AlertCircle, AlertTriangle, CheckCircle2, Loader2, ShieldCheck, Sparkles } from "lucide-react";

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

  const findingsBySeverity = result.findings.reduce<
    Record<AuditSeverity, AuditFinding[]>
  >(
    (acc, f) => {
      acc[f.severity].push(f);
      return acc;
    },
    { critical: [], high: [], medium: [], low: [] },
  );

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
              {items.map((f, idx) => (
                <FindingCard key={`${sev}-${idx}`} finding={f} />
              ))}
            </div>
          );
        },
      )}
    </div>
  );
}

function FindingCard({ finding }: { finding: AuditFinding }) {
  const tone = SEVERITY_TONE[finding.severity];
  return (
    <div className="rounded-xl border border-border/70 bg-card p-4">
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
      </div>
      <blockquote className="mt-2 rounded-md bg-muted/40 px-3 py-2 text-xs italic text-foreground/80">
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
    </div>
  );
}
