import { cn } from "@/lib/utils";

type Props = {
  score: number;
  label?: string;
  sublabel?: string;
  className?: string;
};

function tone(score: number): { color: string; label: string } {
  if (score >= 85) return { color: "text-status-allowed", label: "Konform" };
  if (score >= 60) return { color: "text-status-borderline", label: "Risiko" };
  return { color: "text-status-forbidden", label: "Risiko" };
}

export function ComplianceScore({ score, label = "Compliance-Score", sublabel, className }: Props) {
  const t = tone(score);
  return (
    <div className={cn("rounded-xl border border-border/70 bg-card p-5", className)}>
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div
        className={cn(
          "mt-3 font-serif text-5xl font-semibold leading-none tracking-tight",
          t.color,
        )}
      >
        {score}
      </div>
      <div className="mt-2 text-[11px] text-muted-foreground">
        / 100 · {sublabel ?? t.label}
      </div>
    </div>
  );
}

export function ClaimCountTile({
  count,
  status,
  label,
}: {
  count: number;
  status: "allowed" | "borderline" | "forbidden" | "unclear";
  label: string;
}) {
  const pillColor =
    status === "allowed"
      ? "bg-status-allowed-bg text-status-allowed"
      : status === "borderline"
      ? "bg-status-borderline-bg text-status-borderline"
      : status === "forbidden"
      ? "bg-status-forbidden-bg text-status-forbidden"
      : "bg-status-unclear-bg text-status-unclear";
  const pillLabel =
    status === "allowed"
      ? "Konform"
      : status === "borderline"
      ? "Risiko"
      : status === "forbidden"
      ? "Unzulässig"
      : "Unklar";
  return (
    <div className="rounded-xl border border-border/70 bg-card p-5">
      <span
        className={cn(
          "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
          pillColor,
        )}
      >
        {pillLabel}
      </span>
      <div className="mt-3 font-serif text-4xl font-semibold leading-none tracking-tight">
        {count}
      </div>
      <div className="mt-2 text-[11px] text-muted-foreground">{label}</div>
    </div>
  );
}
