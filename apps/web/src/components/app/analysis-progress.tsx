import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type ProgressStep = {
  id: string;
  label: string;
  detail?: string;
};

export const PIPELINE_STEPS: ProgressStep[] = [
  { id: "normalize", label: "Text normalisieren" },
  { id: "language", label: "Sprache prüfen" },
  { id: "detect", label: "Claims erkennen" },
  { id: "retrieve", label: "Rechtsquellen abrufen" },
  { id: "evaluate", label: "Bewertung erstellen" },
];

type Props = {
  currentStep: number;
  claimsFound?: number;
  claimsEvaluated?: number;
};

export function AnalysisProgress({
  currentStep,
  claimsFound,
  claimsEvaluated,
}: Props) {
  return (
    <ol className="space-y-2">
      {PIPELINE_STEPS.map((step, i) => {
        const done = i < currentStep;
        const active = i === currentStep;
        const pending = i > currentStep;

        let detail: string | undefined;
        if (step.id === "detect" && (done || active) && claimsFound !== undefined) {
          detail = `${claimsFound} Claims gefunden`;
        }
        if (step.id === "evaluate" && active && claimsEvaluated !== undefined && claimsFound) {
          detail = `${claimsEvaluated} von ${claimsFound} bewertet`;
        }

        return (
          <li
            key={step.id}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
              active && "bg-accent/60",
              done && "text-muted-foreground",
              pending && "text-muted-foreground/60",
            )}
          >
            <span className="flex h-5 w-5 shrink-0 items-center justify-center">
              {done ? (
                <span className="grid h-5 w-5 place-items-center rounded-full bg-status-allowed/15 text-status-allowed">
                  <Check className="h-3 w-3" aria-hidden />
                </span>
              ) : active ? (
                <Loader2 className="h-4 w-4 animate-spin text-primary" aria-hidden />
              ) : (
                <span className="h-2 w-2 rounded-full bg-muted-foreground/30" />
              )}
            </span>
            <span className="flex-1 font-medium">{step.label}</span>
            {detail && (
              <span className="font-mono text-[11px] text-muted-foreground">
                {detail}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
