import type { ClaimStatus } from "@/lib/demo-data";
import { cn } from "@/lib/utils";

type Props = {
  counts: Record<ClaimStatus, number>;
  className?: string;
};

const ORDER: ClaimStatus[] = ["allowed", "borderline", "forbidden", "unclear"];
const COLOR: Record<ClaimStatus, string> = {
  allowed: "bg-status-allowed",
  borderline: "bg-status-borderline",
  forbidden: "bg-status-forbidden",
  unclear: "bg-status-unclear",
};

export function AmpelBar({ counts, className }: Props) {
  const total = ORDER.reduce((sum, s) => sum + counts[s], 0);
  const label = ORDER.map((s) => counts[s]).filter((_, i) => ORDER[i] !== "unclear" || counts["unclear"] > 0).join(" · ");

  if (total === 0) {
    return (
      <div className={cn("flex flex-col gap-1", className)}>
        <div className="h-1.5 w-full rounded-full bg-muted" />
        <div className="font-mono text-[11px] text-muted-foreground">0</div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-muted">
        {ORDER.map((status) => {
          const n = counts[status];
          if (n === 0) return null;
          return (
            <div
              key={status}
              className={cn("h-full", COLOR[status])}
              style={{ width: `${(n / total) * 100}%` }}
            />
          );
        })}
      </div>
      <div className="font-mono text-[11px] text-muted-foreground">
        {label}
      </div>
    </div>
  );
}
