import { Check, TriangleAlert, X, HelpCircle, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { STATUS_META, type ClaimStatus } from "@/lib/demo-data";

const STATUS_ICONS: Record<ClaimStatus, LucideIcon> = {
  allowed: Check,
  borderline: TriangleAlert,
  forbidden: X,
  unclear: HelpCircle,
};

const STATUS_STYLES: Record<ClaimStatus, string> = {
  allowed: "bg-status-allowed-bg text-status-allowed ring-1 ring-inset ring-status-allowed/20",
  borderline:
    "bg-status-borderline-bg text-status-borderline ring-1 ring-inset ring-status-borderline/25",
  forbidden:
    "bg-status-forbidden-bg text-status-forbidden ring-1 ring-inset ring-status-forbidden/20",
  unclear:
    "bg-status-unclear-bg text-status-unclear ring-1 ring-inset ring-status-unclear/25",
};

type Props = {
  status: ClaimStatus;
  size?: "sm" | "md";
  className?: string;
};

export function StatusPill({ status, size = "md", className }: Props) {
  const Icon = STATUS_ICONS[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium",
        size === "sm"
          ? "px-2 py-0.5 text-[11px]"
          : "px-2.5 py-1 text-xs",
        STATUS_STYLES[status],
        className,
      )}
      aria-label={`Status: ${STATUS_META[status].label}`}
    >
      <Icon className={cn(size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5")} aria-hidden />
      {STATUS_META[status].label}
    </span>
  );
}
