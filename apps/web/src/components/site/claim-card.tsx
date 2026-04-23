import { Wand2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusPill } from "@/components/site/status-pill";
import type { DemoClaim, ClaimStatus } from "@/lib/demo-data";

const STATUS_BORDER: Record<ClaimStatus, string> = {
  allowed: "border-l-status-allowed",
  borderline: "border-l-status-borderline",
  forbidden: "border-l-status-forbidden",
  unclear: "border-l-status-unclear",
};

type Props = {
  claim: DemoClaim;
  className?: string;
};

export function ClaimCard({ claim, className }: Props) {
  return (
    <article
      className={cn(
        "rounded-lg border border-border/80 bg-card p-5 shadow-sm",
        "border-l-[3px]",
        STATUS_BORDER[claim.status],
        className,
      )}
    >
      <header className="flex items-start justify-between gap-3">
        <h4 className="font-serif text-base leading-tight text-foreground">
          „{claim.text}"
        </h4>
        <StatusPill status={claim.status} />
      </header>

      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
        {claim.reasoning}
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-x-1.5 gap-y-1 font-mono text-[11px] text-muted-foreground/90">
        <svg
          viewBox="0 0 16 16"
          className="h-3.5 w-3.5 shrink-0"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.4"
          aria-hidden
        >
          <path d="M3 3h10v10H3z" />
          <path d="M5.5 6h5M5.5 8.5h3.5" />
        </svg>
        {claim.legalBasis.map((ref, i) => (
          <span key={ref}>
            {ref}
            {i < claim.legalBasis.length - 1 && (
              <span className="mx-1 text-muted-foreground/60">·</span>
            )}
          </span>
        ))}
      </div>

      {claim.rewrite && (
        <div className="mt-4 rounded-md bg-accent/60 p-3">
          <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-accent-foreground/80">
            <Wand2 className="h-3 w-3" aria-hidden />
            Reformulierung
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">
            {claim.rewrite}
          </p>
        </div>
      )}
    </article>
  );
}
