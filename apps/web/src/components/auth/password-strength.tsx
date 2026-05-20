"use client";

// Live password-strength meter using zxcvbn.
//
// Score 0..4 maps to color + German label. Required threshold for
// PROJ-1 is score >= 3. The meter sits below the password input and
// updates on each keystroke. If the user picks something weak, the
// caller can read ``score`` and disable the submit button.

import { useMemo } from "react";
import zxcvbn from "zxcvbn";

type Props = {
  password: string;
};

const LABELS: Record<number, string> = {
  0: "Sehr schwach",
  1: "Schwach",
  2: "Mittel",
  3: "Stark",
  4: "Sehr stark",
};

const BAR_COLORS: Record<number, string> = {
  0: "bg-status-forbidden",
  1: "bg-status-forbidden",
  2: "bg-status-borderline",
  3: "bg-status-allowed",
  4: "bg-status-allowed",
};

export function PasswordStrength({ password }: Props) {
  const result = useMemo(() => {
    if (!password) return null;
    // zxcvbn is a sync CPU job; harmless on every keystroke for the
    // lengths we expect here.
    return zxcvbn(password);
  }, [password]);

  if (!password) return null;

  const score = result?.score ?? 0;
  const warning = result?.feedback?.warning ?? "";
  const suggestions = result?.feedback?.suggestions ?? [];

  return (
    <div className="space-y-1.5 text-xs">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((idx) => (
          <div
            key={idx}
            className={`h-1.5 flex-1 rounded-full transition-colors ${
              idx < score ? BAR_COLORS[score] : "bg-border"
            }`}
          />
        ))}
      </div>
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-medium text-foreground">{LABELS[score]}</span>
        {warning ? <span className="text-muted-foreground">{warning}</span> : null}
      </div>
      {suggestions.length > 0 ? (
        <p className="text-muted-foreground">{suggestions.join(" ")}</p>
      ) : null}
    </div>
  );
}

/** Pure helper so pages can gate submit on a strong score. */
export function getPasswordScore(password: string): number {
  if (!password) return 0;
  return zxcvbn(password).score;
}
