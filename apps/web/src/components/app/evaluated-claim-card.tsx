import { Copy, Scale, Wand2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  EvaluatedClaim,
  EvaluationStatus,
} from "@/lib/api-client";
import { StatusPill } from "@/components/site/status-pill";

const STATUS_BORDER: Record<EvaluationStatus, string> = {
  allowed: "border-l-status-allowed",
  borderline: "border-l-status-borderline",
  forbidden: "border-l-status-forbidden",
  unclear: "border-l-status-unclear",
};

const RISK_LABELS = {
  low: "Niedrig",
  medium: "Mittel",
  high: "Hoch",
} as const;

const RISK_TONES = {
  low: "bg-status-allowed-bg text-status-allowed",
  medium: "bg-status-borderline-bg text-status-borderline",
  high: "bg-status-forbidden-bg text-status-forbidden",
} as const;

type Props = {
  claim: EvaluatedClaim;
  index: number;
  isActive?: boolean;
  onSelect?: () => void;
};

export function EvaluatedClaimCard({ claim, index, isActive, onSelect }: Props) {
  const confidencePercent = Math.round(claim.confidence * 100);
  return (
    <article
      id={`claim-${claim.id}`}
      data-claim-id={claim.id}
      onClick={onSelect}
      className={cn(
        "rounded-lg border border-border/80 bg-card p-5 shadow-sm transition-shadow",
        "border-l-[3px]",
        STATUS_BORDER[claim.status],
        isActive && "ring-2 ring-primary/40",
        onSelect && "cursor-pointer hover:shadow",
      )}
    >
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            #{index} · {claim.implicitness === "explicit" ? "explizit" : "implizit"}
            {claim.nutrient && ` · ${claim.nutrient}`}
          </span>
          <h4 className="mt-1 font-serif text-base leading-tight text-foreground">
            „{claim.claim_text}"
          </h4>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <StatusPill status={claim.status} />
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium",
              RISK_TONES[claim.risk_level],
            )}
          >
            Risiko: {RISK_LABELS[claim.risk_level]}
          </span>
        </div>
      </header>

      <p className="mt-3 text-sm leading-relaxed text-foreground/85">
        {claim.reasoning}
      </p>

      {claim.legal_hints.length > 0 && (
        <div className="mt-4 rounded-md bg-muted/40 p-3">
          <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            <Scale className="h-3 w-3" aria-hidden />
            Mögliche Rechtsgrundlage (KI-Schätzung)
          </div>
          <ul className="mt-2 space-y-1.5 text-sm">
            {claim.legal_hints.map((hint, i) => (
              <li key={i}>
                <span className="font-mono text-[12px] text-foreground">
                  {hint.reference}
                </span>
                <span className="text-foreground/70"> — {hint.rationale}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {claim.rewrite_suggestion && (
        <div className="mt-3 rounded-md bg-accent/60 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-accent-foreground/80">
              <Wand2 className="h-3 w-3" aria-hidden />
              Reformulierungsvorschlag
            </div>
            <CopyButton text={claim.rewrite_suggestion} />
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">
            {claim.rewrite_suggestion}
          </p>
        </div>
      )}

      <div className="mt-3 flex items-center justify-between text-[11px] text-muted-foreground">
        <span>Confidence: {confidencePercent}%</span>
        <span className="font-mono">
          {claim.evaluation_model} · v{claim.evaluation_prompt_version}
        </span>
      </div>
    </article>
  );
}

function CopyButton({ text }: { text: string }) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        void navigator.clipboard.writeText(text);
      }}
      className="inline-flex items-center gap-1 rounded text-[11px] font-medium text-accent-foreground/70 transition-colors hover:text-accent-foreground"
    >
      <Copy className="h-3 w-3" aria-hidden />
      Kopieren
    </button>
  );
}
