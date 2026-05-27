import {
  BadgeCheck,
  BookOpen,
  Check,
  Copy,
  ExternalLink,
  Gavel,
  Leaf,
  RotateCcw,
  Scale,
  Scissors,
  Wand2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  isDeleteMarker,
  type EvaluatedClaim,
  type EvaluationStatus,
  type RetrievalHit,
  type RetrievalSourceType,
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
  isApplied?: boolean;
  onSelect?: () => void;
  onApply?: () => void;
  onRevert?: () => void;
};

export function EvaluatedClaimCard({
  claim,
  index,
  isActive,
  isApplied,
  onSelect,
  onApply,
  onRevert,
}: Props) {
  const confidencePercent = Math.round(claim.confidence * 100);
  return (
    <article
      id={`claim-${claim.id}`}
      data-claim-id={claim.id}
      onClick={onSelect}
      className={cn(
        "rounded-lg border border-border/80 bg-card p-5 shadow-sm transition-all",
        "border-l-[3px]",
        STATUS_BORDER[claim.status],
        isActive && "ring-2 ring-primary/40",
        isApplied && "border-status-allowed/50 bg-status-allowed-bg/30",
        onSelect && "cursor-pointer hover:shadow",
      )}
    >
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            #{index} · {claim.implicitness === "explicit" ? "explizit" : "implizit"}
            {claim.nutrient && ` · ${claim.nutrient}`}
          </span>
          <h4
            className={cn(
              "mt-1 font-serif text-base leading-tight text-foreground",
              isApplied && "text-muted-foreground line-through",
            )}
          >
            „{claim.claim_text}"
          </h4>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          {isApplied ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-status-allowed-bg px-2.5 py-1 text-[11px] font-medium text-status-allowed">
              <Check className="h-3 w-3" aria-hidden />
              Übernommen
            </span>
          ) : (
            <StatusPill status={claim.status} />
          )}
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

      {!isApplied && (
        <p className="mt-3 text-sm leading-relaxed text-foreground/85">
          {claim.reasoning}
        </p>
      )}

      {!isApplied && claim.evidence.length > 0 && (
        <EvidenceSection evidence={claim.evidence} />
      )}

      {!isApplied && claim.legal_hints.length > 0 && (
        <LegalHintsSection hints={claim.legal_hints} />
      )}

      {claim.rewrite_suggestion && isDeleteMarker(claim.rewrite_suggestion) && (
        <div
          className={cn(
            "mt-3 rounded-md border-l-2 p-3",
            isApplied
              ? "border-status-allowed/60 bg-status-allowed-bg/60"
              : "border-status-forbidden/60 bg-status-forbidden-bg/30",
          )}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-status-forbidden">
              <Scissors className="h-3 w-3" aria-hidden />
              {isApplied ? "Gestrichen" : "Streichen empfohlen"}
            </div>
            <div className="flex items-center gap-2">
              {!isApplied && onApply && <ApplyButton onClick={onApply} label="Streichen" />}
              {isApplied && onRevert && <RevertButton onClick={onRevert} />}
            </div>
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-foreground/85">
            Für diese Aussage ist keine HCVO-konforme Reformulierung möglich,
            ohne den Sinn zu verfehlen. Beim Streichen wird der Satz
            ersatzlos aus dem Marketing-Text entfernt — die umliegenden
            Sätze bleiben unverändert.
          </p>
        </div>
      )}

      {claim.rewrite_suggestion && !isDeleteMarker(claim.rewrite_suggestion) && (
        <div
          className={cn(
            "mt-3 rounded-md p-3",
            isApplied ? "bg-status-allowed-bg/60" : "bg-accent/60",
          )}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-accent-foreground/80">
              <Wand2 className="h-3 w-3" aria-hidden />
              {isApplied ? "Übernommene Reformulierung" : "Reformulierungsvorschlag"}
            </div>
            <div className="flex items-center gap-2">
              {!isApplied && <CopyButton text={claim.rewrite_suggestion} />}
              {!isApplied && onApply && (
                <ApplyButton onClick={onApply} />
              )}
              {isApplied && onRevert && (
                <RevertButton onClick={onRevert} />
              )}
            </div>
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">
            {claim.rewrite_suggestion}
          </p>
        </div>
      )}

      {!isApplied && (
        <div className="mt-3 flex items-center justify-between text-[11px] text-muted-foreground">
          <span>Confidence: {confidencePercent}%</span>
          <span className="font-mono">
            {claim.evaluation_model} · v{claim.evaluation_prompt_version}
          </span>
        </div>
      )}
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

function ApplyButton({
  onClick,
  label = "Anwenden",
}: {
  onClick: () => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className="inline-flex items-center gap-1 rounded bg-primary px-2 py-1 text-[11px] font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
    >
      <Check className="h-3 w-3" aria-hidden />
      {label}
    </button>
  );
}

function RevertButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className="inline-flex items-center gap-1 rounded text-[11px] font-medium text-muted-foreground transition-colors hover:text-foreground"
    >
      <RotateCcw className="h-3 w-3" aria-hidden />
      Rückgängig
    </button>
  );
}

const SOURCE_LABEL: Record<RetrievalSourceType, string> = {
  eu_claim: "EU-Register",
  regulation: "Rechtsnorm",
  case_law: "Rechtsprechung",
  botanical: "Botanical (EFSA)",
};

const SOURCE_ICON: Record<RetrievalSourceType, typeof BookOpen> = {
  eu_claim: BadgeCheck,
  regulation: BookOpen,
  case_law: Gavel,
  botanical: Leaf,
};

function EvidenceSection({ evidence }: { evidence: RetrievalHit[] }) {
  return (
    <div className="mt-4 rounded-md border border-status-allowed/30 bg-status-allowed-bg/30 p-3">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-status-allowed">
        <BadgeCheck className="h-3 w-3" aria-hidden />
        Belege aus der Wissensbasis
      </div>
      <ul className="mt-2 space-y-2">
        {evidence.map((hit) => {
          const Icon = SOURCE_ICON[hit.source_type];
          return (
            <li
              key={hit.chunk_id}
              className="rounded border border-border/60 bg-background/80 p-2"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  <Icon className="h-3 w-3" aria-hidden />
                  {SOURCE_LABEL[hit.source_type]}
                </span>
                <span className="font-mono text-[10px] text-muted-foreground">
                  Score {hit.score.toFixed(2)}
                </span>
              </div>
              <div className="mt-1 font-mono text-[12px] text-foreground">
                {hit.reference}
              </div>
              <p className="mt-1 text-[13px] leading-relaxed text-foreground/85">
                {hit.snippet}
              </p>
              {hit.url && (
                <a
                  href={hit.url}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline"
                >
                  <ExternalLink className="h-3 w-3" aria-hidden />
                  Quelle öffnen
                </a>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function LegalHintsSection({ hints }: { hints: { reference: string; rationale: string; verified: boolean; chunk_id: string | null; url: string | null }[] }) {
  const allVerified = hints.every((h) => h.verified);
  return (
    <div className="mt-3 rounded-md bg-muted/40 p-3">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        <Scale className="h-3 w-3" aria-hidden />
        Rechtliche Einordnung{allVerified ? "" : " (teils KI-Schätzung)"}
      </div>
      <ul className="mt-2 space-y-1.5 text-sm">
        {hints.map((hint, i) => (
          <li key={i}>
            <span className="font-mono text-[12px] text-foreground">
              {hint.reference}
            </span>
            {hint.verified ? (
              <span className="ml-1.5 inline-flex items-center gap-0.5 rounded-full bg-status-allowed-bg px-1.5 py-0 text-[10px] font-medium text-status-allowed align-middle">
                <BadgeCheck className="h-2.5 w-2.5" aria-hidden />
                verifiziert
              </span>
            ) : (
              <span className="ml-1.5 inline-block rounded-full bg-muted px-1.5 py-0 text-[10px] font-medium text-muted-foreground align-middle">
                KI-Schätzung
              </span>
            )}
            <span className="text-foreground/70"> — {hint.rationale}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
