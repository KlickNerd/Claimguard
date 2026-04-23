import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

type Props = {
  label: string;
  value: string;
  sublabel?: string;
  delta?: string;
  deltaTone?: "positive" | "neutral" | "warning";
  icon: LucideIcon;
  valueClassName?: string;
};

export function KpiCard({
  label,
  value,
  sublabel,
  delta,
  deltaTone = "neutral",
  icon: Icon,
  valueClassName,
}: Props) {
  return (
    <div className="rounded-xl border border-border/70 bg-card p-5">
      <div className="flex items-start justify-between">
        <span className="text-xs font-medium text-muted-foreground">
          {label}
        </span>
        <span
          className={cn(
            "grid h-8 w-8 place-items-center rounded-md",
            "bg-accent/70 text-accent-foreground",
          )}
        >
          <Icon className="h-4 w-4" aria-hidden />
        </span>
      </div>

      <div className="mt-3 flex items-end gap-2">
        <span
          className={cn(
            "font-serif text-4xl font-semibold leading-none tracking-tight",
            valueClassName,
          )}
        >
          {value}
        </span>
      </div>

      <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
        {delta && (
          <span
            className={cn(
              "font-mono",
              deltaTone === "positive" && "text-status-allowed",
              deltaTone === "warning" && "text-status-borderline",
            )}
          >
            {delta}
          </span>
        )}
        {sublabel && <span>{sublabel}</span>}
      </div>
    </div>
  );
}
