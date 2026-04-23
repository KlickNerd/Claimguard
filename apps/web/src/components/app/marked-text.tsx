import type { DemoClaim } from "@/lib/demo-data";
import { cn } from "@/lib/utils";

const HIGHLIGHT: Record<DemoClaim["status"], string> = {
  allowed:
    "bg-status-allowed-bg text-status-allowed decoration-status-allowed/60",
  borderline:
    "bg-status-borderline-bg text-status-borderline decoration-status-borderline/70",
  forbidden:
    "bg-status-forbidden-bg text-status-forbidden decoration-status-forbidden/70",
  unclear:
    "bg-status-unclear-bg text-status-unclear decoration-status-unclear/60",
};

type Segment =
  | { kind: "text"; value: string }
  | { kind: "claim"; value: string; status: DemoClaim["status"]; id: string };

function buildSegments(text: string, claims: DemoClaim[]): Segment[] {
  const matches: { start: number; end: number; claim: DemoClaim }[] = [];
  for (const claim of claims) {
    const idx = text.indexOf(claim.text);
    if (idx >= 0) {
      matches.push({ start: idx, end: idx + claim.text.length, claim });
    }
  }
  matches.sort((a, b) => a.start - b.start);

  const segments: Segment[] = [];
  let cursor = 0;
  for (const m of matches) {
    if (m.start > cursor) {
      segments.push({ kind: "text", value: text.slice(cursor, m.start) });
    }
    segments.push({
      kind: "claim",
      value: text.slice(m.start, m.end),
      status: m.claim.status,
      id: m.claim.id,
    });
    cursor = m.end;
  }
  if (cursor < text.length) {
    segments.push({ kind: "text", value: text.slice(cursor) });
  }
  return segments;
}

type Props = {
  text: string;
  claims: DemoClaim[];
};

export function MarkedText({ text, claims }: Props) {
  const segments = buildSegments(text, claims);
  return (
    <p className="font-serif text-base leading-[1.8] text-foreground">
      {segments.map((s, i) =>
        s.kind === "text" ? (
          <span key={i}>{s.value}</span>
        ) : (
          <mark
            key={i}
            className={cn(
              "rounded px-1 py-0.5 underline decoration-2 underline-offset-4",
              HIGHLIGHT[s.status],
            )}
            data-claim-id={s.id}
          >
            {s.value}
          </mark>
        ),
      )}
    </p>
  );
}
