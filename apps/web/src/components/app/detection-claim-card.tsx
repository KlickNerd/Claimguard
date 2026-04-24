import type { DetectedClaim } from "@/lib/api-client";
import { cn } from "@/lib/utils";

const TYPE_META: Record<
  DetectedClaim["claim_type"],
  { label: string; tone: string }
> = {
  nutrient_based: {
    label: "Nährstoffbezogen",
    tone: "bg-status-allowed-bg text-status-allowed",
  },
  health_based: {
    label: "Gesundheitsbezogen",
    tone: "bg-accent text-accent-foreground",
  },
  reduction_based: {
    label: "Risikoreduktion",
    tone: "bg-status-borderline-bg text-status-borderline",
  },
  wellbeing_based: {
    label: "Wohlbefinden (implizit)",
    tone: "bg-status-borderline-bg text-status-borderline",
  },
  disease_based: {
    label: "Krankheitsbezogen",
    tone: "bg-status-forbidden-bg text-status-forbidden",
  },
};

const BORDER_TONE: Record<DetectedClaim["claim_type"], string> = {
  nutrient_based: "border-l-status-allowed",
  health_based: "border-l-accent-foreground",
  reduction_based: "border-l-status-borderline",
  wellbeing_based: "border-l-status-borderline",
  disease_based: "border-l-status-forbidden",
};

type Props = {
  claim: DetectedClaim;
};

export function DetectionClaimCard({ claim }: Props) {
  const meta = TYPE_META[claim.claim_type];
  return (
    <article
      className={cn(
        "rounded-lg border border-border/80 bg-card p-5 shadow-sm",
        "border-l-[3px]",
        BORDER_TONE[claim.claim_type],
      )}
    >
      <header className="flex items-start justify-between gap-3">
        <h4 className="font-serif text-base leading-tight text-foreground">
          „{claim.claim_text}"
        </h4>
        <span
          className={cn(
            "inline-flex shrink-0 items-center rounded-full px-2.5 py-1 text-[11px] font-medium",
            meta.tone,
          )}
        >
          {meta.label}
        </span>
      </header>

      <dl className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <dt className="font-medium text-foreground/70">Art:</dt>
          <dd>{claim.implicitness === "explicit" ? "explizit" : "implizit"}</dd>
        </div>
        {claim.nutrient && (
          <div className="flex items-center gap-1">
            <dt className="font-medium text-foreground/70">Nährstoff:</dt>
            <dd>{claim.nutrient}</dd>
          </div>
        )}
        {claim.substance && (
          <div className="flex items-center gap-1">
            <dt className="font-medium text-foreground/70">Substanz:</dt>
            <dd>{claim.substance}</dd>
          </div>
        )}
        <div className="flex items-center gap-1 font-mono">
          <dt className="font-medium text-foreground/70">Pos:</dt>
          <dd>
            {claim.position_start}–{claim.position_end}
          </dd>
        </div>
      </dl>
    </article>
  );
}
