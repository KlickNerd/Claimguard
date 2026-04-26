import { cn } from "@/lib/utils";
import type { DetectedClaim, EvaluatedClaim, EvaluationStatus } from "@/lib/api-client";

const STATUS_HIGHLIGHT: Record<EvaluationStatus, string> = {
  allowed: "bg-status-allowed-bg/80 text-status-allowed decoration-status-allowed/40",
  borderline:
    "bg-status-borderline-bg/80 text-status-borderline decoration-status-borderline/50",
  forbidden:
    "bg-status-forbidden-bg/80 text-status-forbidden decoration-status-forbidden/40",
  unclear:
    "bg-status-unclear-bg/80 text-status-unclear decoration-status-unclear/40",
};

const NEUTRAL_HIGHLIGHT =
  "bg-accent text-accent-foreground decoration-accent-foreground/30";

type HighlightClaim = DetectedClaim | EvaluatedClaim;

type Segment =
  | { kind: "text"; value: string }
  | {
      kind: "claim";
      value: string;
      claim: HighlightClaim;
      status: EvaluationStatus | null;
      index: number;
    };

function buildSegments(
  text: string,
  claims: HighlightClaim[],
  evaluatedById: Map<string, EvaluatedClaim>,
): Segment[] {
  // Sort by position, drop overlaps (keep the earlier one).
  const sorted = [...claims].sort(
    (a, b) => a.position_start - b.position_start,
  );
  const segments: Segment[] = [];
  let cursor = 0;
  let visualIndex = 0;
  for (const claim of sorted) {
    if (claim.position_start < cursor) continue;
    if (claim.position_start > cursor) {
      segments.push({
        kind: "text",
        value: text.slice(cursor, claim.position_start),
      });
    }
    const evaluated = evaluatedById.get(claim.id);
    segments.push({
      kind: "claim",
      value: text.slice(claim.position_start, claim.position_end),
      claim: evaluated ?? claim,
      status: evaluated?.status ?? null,
      index: ++visualIndex,
    });
    cursor = claim.position_end;
  }
  if (cursor < text.length) {
    segments.push({ kind: "text", value: text.slice(cursor) });
  }
  return segments;
}

type Props = {
  text: string;
  detectedClaims: DetectedClaim[];
  evaluatedClaims: EvaluatedClaim[];
  onClaimClick?: (claimId: string) => void;
  activeClaimId?: string | null;
};

export function HighlightedText({
  text,
  detectedClaims,
  evaluatedClaims,
  onClaimClick,
  activeClaimId,
}: Props) {
  const evaluatedById = new Map(evaluatedClaims.map((c) => [c.id, c]));
  // Prefer the evaluated list when available so highlights pick up status,
  // fall back to the raw detection list otherwise (e.g. evaluation skipped).
  const sourceList: HighlightClaim[] =
    evaluatedClaims.length > 0 ? evaluatedClaims : detectedClaims;

  const segments = buildSegments(text, sourceList, evaluatedById);

  return (
    <div className="overflow-y-auto px-5 py-5">
      <p className="whitespace-pre-wrap font-serif text-[15px] leading-[1.85] text-foreground">
        {segments.map((s, i) =>
          s.kind === "text" ? (
            <span key={i}>{s.value}</span>
          ) : (
            <button
              key={i}
              type="button"
              data-claim-id={s.claim.id}
              onClick={() => onClaimClick?.(s.claim.id)}
              className={cn(
                "rounded px-1 py-0.5 underline decoration-2 underline-offset-4 transition-shadow",
                "cursor-pointer ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                s.status
                  ? STATUS_HIGHLIGHT[s.status]
                  : NEUTRAL_HIGHLIGHT,
                activeClaimId === s.claim.id &&
                  "ring-2 ring-primary ring-offset-1",
              )}
              aria-label={`Claim ${s.index}: ${s.claim.claim_text}`}
            >
              {s.value}
            </button>
          ),
        )}
      </p>
    </div>
  );
}
