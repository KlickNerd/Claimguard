import type { ComponentProps } from "react";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import remarkGfm from "remark-gfm";
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

const APPLIED_HIGHLIGHT =
  "bg-status-allowed-bg text-status-allowed decoration-status-allowed/60 italic";

const NEUTRAL_HIGHLIGHT =
  "bg-accent text-accent-foreground decoration-accent-foreground/30";

type HighlightClaim = DetectedClaim | EvaluatedClaim;

/** Splice the claim spans into the source text as inline ``<mark>`` tags so
 *  react-markdown + rehype-raw can render them through any block-level
 *  element (headings, bullets, paragraphs, tables) that surrounds them.
 *
 *  Position indices stay relative to the *original* markdown source - we
 *  only swap the visible text of applied claims, never the indices for
 *  subsequent ones, so headings/bullets stay anchored to the right
 *  characters even after rewrites are applied. */
function annotateMarkdown(
  text: string,
  claims: HighlightClaim[],
  evaluatedById: Map<string, EvaluatedClaim>,
  appliedIds: Set<string>,
  activeClaimId: string | null,
): string {
  const sorted = [...claims].sort(
    (a, b) => a.position_start - b.position_start,
  );
  let out = "";
  let cursor = 0;
  let visualIndex = 0;
  for (const claim of sorted) {
    if (claim.position_start < cursor) continue;
    if (claim.position_start > cursor) {
      out += text.slice(cursor, claim.position_start);
    }
    visualIndex += 1;
    const evaluated = evaluatedById.get(claim.id);
    const applied =
      appliedIds.has(claim.id) && Boolean(evaluated?.rewrite_suggestion);
    const innerRaw = applied && evaluated?.rewrite_suggestion
      ? evaluated.rewrite_suggestion
      : text.slice(claim.position_start, claim.position_end);
    // ``<mark>`` keeps inline semantics across markdown blocks. Replace
    // newlines inside the claim with a literal break so the text stays on
    // the same paragraph after parsing - long claims that straddle a
    // markdown boundary would otherwise tear the document apart.
    const inner = escapeHtml(innerRaw).replace(/\n/g, " ");
    out += `<mark data-claim-id="${claim.id}" data-status="${
      evaluated?.status ?? ""
    }" data-applied="${applied ? "1" : "0"}" data-active="${
      activeClaimId === claim.id ? "1" : "0"
    }" data-index="${visualIndex}">${inner}</mark>`;
    cursor = claim.position_end;
  }
  if (cursor < text.length) out += text.slice(cursor);
  return out;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

type Props = {
  text: string;
  detectedClaims: DetectedClaim[];
  evaluatedClaims: EvaluatedClaim[];
  onClaimClick?: (claimId: string) => void;
  activeClaimId?: string | null;
  appliedIds?: Set<string>;
};

export function HighlightedText({
  text,
  detectedClaims,
  evaluatedClaims,
  onClaimClick,
  activeClaimId,
  appliedIds,
}: Props) {
  const evaluatedById = new Map(evaluatedClaims.map((c) => [c.id, c]));
  const sourceList: HighlightClaim[] =
    evaluatedClaims.length > 0 ? evaluatedClaims : detectedClaims;

  const annotated = annotateMarkdown(
    text,
    sourceList,
    evaluatedById,
    appliedIds ?? new Set<string>(),
    activeClaimId ?? null,
  );

  return (
    <div className="prose prose-sm max-w-none overflow-y-auto px-5 py-5 font-serif text-[15px] leading-[1.85] text-foreground prose-headings:font-serif prose-headings:tracking-tight prose-headings:text-foreground prose-strong:text-foreground prose-a:text-primary prose-li:my-1">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          mark: (props) => (
            <ClaimMark
              {...(props as ComponentProps<"mark"> & {
                "data-claim-id"?: string;
                "data-status"?: string;
                "data-applied"?: string;
                "data-active"?: string;
                "data-index"?: string;
              })}
              onClaimClick={onClaimClick}
            />
          ),
        }}
      >
        {annotated}
      </ReactMarkdown>
    </div>
  );
}

function ClaimMark({
  onClaimClick,
  children,
  ...attrs
}: ComponentProps<"mark"> & {
  "data-claim-id"?: string;
  "data-status"?: string;
  "data-applied"?: string;
  "data-active"?: string;
  "data-index"?: string;
  onClaimClick?: (claimId: string) => void;
}) {
  const claimId = attrs["data-claim-id"] ?? "";
  const status = (attrs["data-status"] ?? "") as EvaluationStatus | "";
  const applied = attrs["data-applied"] === "1";
  const active = attrs["data-active"] === "1";
  const index = attrs["data-index"] ?? "";

  // Strip our private data-* attrs from the spread so React doesn't
  // forward them as unknown DOM props during type narrowing.
  const {
    "data-claim-id": _id,
    "data-status": _status,
    "data-applied": _applied,
    "data-active": _active,
    "data-index": _index,
    ...rest
  } = attrs;
  void _id;
  void _status;
  void _applied;
  void _active;
  void _index;

  return (
    <button
      {...(rest as ComponentProps<"button">)}
      type="button"
      data-claim-id={claimId}
      onClick={() => claimId && onClaimClick?.(claimId)}
      className={cn(
        "rounded px-1 py-0.5 underline decoration-2 underline-offset-4 transition-shadow",
        "cursor-pointer ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        applied
          ? APPLIED_HIGHLIGHT
          : status
            ? STATUS_HIGHLIGHT[status as EvaluationStatus]
            : NEUTRAL_HIGHLIGHT,
        active && "ring-2 ring-primary ring-offset-1",
      )}
      aria-label={
        applied
          ? `Claim ${index}: Reformulierung übernommen`
          : `Claim ${index}`
      }
    >
      {children}
    </button>
  );
}
