"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Activity,
  AlertCircle,
  Check,
  CheckCheck,
  Clipboard,
  Download,
  FileText,
  Info,
  Link2,
  MoreHorizontal,
  Pencil,
  RefreshCcw,
  RotateCcw,
  Scan,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  TriangleAlert,
  Upload,
} from "lucide-react";
import { AppHeader } from "@/components/app/app-header";
import { KpiCard } from "@/components/app/kpi-card";
import {
  AnalysisProgress,
  PIPELINE_STEPS,
} from "@/components/app/analysis-progress";
import { DetectionClaimCard } from "@/components/app/detection-claim-card";
import { EvaluatedClaimCard } from "@/components/app/evaluated-claim-card";
import { HighlightedText } from "@/components/app/highlighted-text";
import { MarkdownEditor } from "@/components/app/markdown-editor";
import { FinalAuditPanel } from "@/components/app/final-audit-panel";
import { PdfDropzone } from "@/components/app/pdf-dropzone";
import { UrlInput } from "@/components/app/url-input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { KPIS } from "@/lib/mock-analyses";
import { DEMO_INPUT } from "@/lib/demo-data";
import {
  AnalysisError,
  applyAuditFindings,
  createAnalysis,
  isDeleteMarker,
  polishText,
  rewriteAllClaims,
  runFinalAudit,
  smartApplyClaims,
  type AnalysisResponse,
  type DetectedClaim,
  type EvaluatedClaim,
  type FinalAuditResult,
} from "@/lib/api-client";
import { downloadAsDoc } from "@/lib/export-doc";

const TABS = [
  { id: "text" as const, label: "Text", icon: FileText },
  { id: "url" as const, label: "URL", icon: Link2 },
  { id: "pdf" as const, label: "PDF", icon: Upload },
];

type Phase = "idle" | "running" | "done" | "error";

const STEP_DELAYS_MS = [500, 500, 500];

const MIN_CHARS = 50;
const MAX_CHARS = 50_000;
const WARN_THRESHOLD = 0.9;

const QUOTE_PAIRS: Array<readonly [string, string]> = [
  ["„", "“"],
  ["“", "”"],
  ["«", "»"],
  ["'", "'"],
  ["‘", "’"],
  ['"', '"'],
];

const TERMINAL_PUNCT = ".!?";

/** Make the rewrite slot cleanly into the surrounding text:
 *  - strip wrapping quotes the LLM occasionally leaves on the rewrite
 *  - match terminal punctuation to the original claim's so a mid-
 *    sentence claim doesn't end up with ". und …" after the splice.
 */
function normaliseRewrite(rewrite: string, originalClaim: string): string {
  let cleaned = rewrite.trim();
  // Drop matched quote pairs (possibly nested).
  while (cleaned.length >= 2) {
    const first = cleaned[0];
    const last = cleaned[cleaned.length - 1];
    const match = QUOTE_PAIRS.find(([o, c]) => first === o && last === c);
    if (!match) break;
    cleaned = cleaned.slice(1, -1).trim();
  }
  if (!cleaned) return cleaned;
  const originalTrim = originalClaim.trimEnd();
  const originalLast = originalTrim.slice(-1);
  const cleanedLast = cleaned.slice(-1);
  if (TERMINAL_PUNCT.includes(originalLast)) {
    if (!TERMINAL_PUNCT.includes(cleanedLast)) {
      cleaned = cleaned.replace(/\s+$/, "") + originalLast;
    }
  } else if (TERMINAL_PUNCT.includes(cleanedLast)) {
    cleaned = cleaned.replace(/[.!?]+\s*$/, "").trimEnd();
  }
  return cleaned;
}

/**
 * Apply rewrites in descending position order so earlier claims keep their
 * original positions while we patch the text. Returns the rewritten string.
 */
function applyRewritesToText(
  originalText: string,
  evaluatedClaims: EvaluatedClaim[],
  appliedIds: Set<string>,
): string {
  const ordered = evaluatedClaims
    .filter((c) => appliedIds.has(c.id) && c.rewrite_suggestion)
    .sort((a, b) => b.position_start - a.position_start);

  let text = originalText;
  for (const claim of ordered) {
    const suggestion = claim.rewrite_suggestion ?? "";
    // [DELETE] sentinel: the LLM signalled "no compliant rewrite
    // possible - drop the claim entirely". Splice in an empty string
    // and collapse any double whitespace the removal might leave.
    if (isDeleteMarker(suggestion)) {
      text =
        text.slice(0, claim.position_start) + text.slice(claim.position_end);
      continue;
    }
    const rewrite = normaliseRewrite(suggestion, claim.claim_text);
    text =
      text.slice(0, claim.position_start) +
      rewrite +
      text.slice(claim.position_end);
  }
  // Collapse double-spaces / orphan punctuation introduced by deletions.
  return text.replace(/  +/g, " ").replace(/\s+([.,;:!?])/g, "$1");
}

export default function AppHomePage() {
  const [activeTab, setActiveTab] = useState<"text" | "url" | "pdf">("text");
  const [input, setInput] = useState(DEMO_INPUT);
  const [phase, setPhase] = useState<Phase>("idle");
  const [currentStep, setCurrentStep] = useState(0);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeClaimId, setActiveClaimId] = useState<string | null>(null);
  const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());
  const [copyHint, setCopyHint] = useState(false);
  const [pdfFilename, setPdfFilename] = useState<string | null>(null);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [isRewritingAll, setIsRewritingAll] = useState(false);
  const [rewriteAllError, setRewriteAllError] = useState<string | null>(null);
  const [polishedText, setPolishedText] = useState<string | null>(null);
  const [polishSummary, setPolishSummary] = useState<string>("");
  const [isPolishing, setIsPolishing] = useState(false);
  const [polishError, setPolishError] = useState<string | null>(null);
  // Convergence-check residuals from smart-apply: claims that are still
  // detected in the rewritten text. Non-empty list means the rewrite
  // didn't converge and the user should manually review.
  const [smartApplyResidual, setSmartApplyResidual] = useState<DetectedClaim[]>([]);
  // Final-audit state (Opus 4.7 holistic compliance review).
  const [finalAuditResult, setFinalAuditResult] = useState<FinalAuditResult | null>(null);
  const [isAuditing, setIsAuditing] = useState(false);
  const [auditError, setAuditError] = useState<string | null>(null);
  // Indices into ``finalAuditResult.findings`` that the user already
  // applied via the panel's "Übernehmen"-button. Reset when a new audit
  // runs or the polish is reverted.
  const [appliedAuditFindings, setAppliedAuditFindings] = useState<Set<number>>(
    new Set(),
  );
  // "One-shot LLM rewrite all findings"-button state.
  const [isApplyingAuditByLLM, setIsApplyingAuditByLLM] = useState(false);
  const [applyAuditByLLMError, setApplyAuditByLLMError] = useState<string | null>(null);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(
    () => () => {
      timers.current.forEach(clearTimeout);
    },
    [],
  );

  const clearTimers = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };

  const runAnalysis = async (overrideInput?: string) => {
    const text = overrideInput ?? input;
    clearTimers();
    setPhase("running");
    setCurrentStep(0);
    setResult(null);
    setError(null);
    setAppliedIds(new Set());

    let cumulative = 0;
    for (let i = 0; i < STEP_DELAYS_MS.length; i++) {
      cumulative += STEP_DELAYS_MS[i];
      timers.current.push(
        setTimeout(() => setCurrentStep(i + 1), cumulative),
      );
    }

    try {
      const sourceType: "text" | "url" | "pdf" = pdfFilename
        ? "pdf"
        : sourceUrl
          ? "url"
          : "text";
      const response = await createAnalysis({
        input_text: text,
        source_type: sourceType,
        source_reference: pdfFilename ?? sourceUrl ?? null,
      });
      clearTimers();
      setCurrentStep(PIPELINE_STEPS.length);
      setResult(response);
      setPhase("done");
    } catch (err) {
      clearTimers();
      if (err instanceof AnalysisError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unbekannter Fehler bei der Analyse.");
      }
      setPhase("error");
    }
  };

  const resetAnalysis = () => {
    clearTimers();
    setPhase("idle");
    setCurrentStep(0);
    setResult(null);
    setError(null);
    setActiveClaimId(null);
    setAppliedIds(new Set());
    setPdfFilename(null);
    setSourceUrl(null);
    setPolishedText(null);
    setPolishSummary("");
    setPolishError(null);
    setSmartApplyResidual([]);
    setFinalAuditResult(null);
    setAuditError(null);
    setAppliedAuditFindings(new Set());
  };

  /** Run Sonnet over the rewritten text to fix grammar / transitions
   *  without touching compliance. Result replaces the displayed body
   *  until reverted. */
  const polish = async () => {
    if (!result || isPolishing) return;
    const sourceText = applyRewritesToText(
      result.input_text,
      result.evaluated_claims,
      appliedIds,
    );
    setIsPolishing(true);
    setPolishError(null);
    try {
      const response = await polishText(sourceText);
      setPolishedText(response.polished_text);
      setPolishSummary(response.change_summary);
    } catch (err) {
      if (err instanceof AnalysisError) {
        setPolishError(err.message);
      } else if (err instanceof Error) {
        setPolishError(err.message);
      } else {
        setPolishError("Schluss-Korrektur fehlgeschlagen.");
      }
    } finally {
      setIsPolishing(false);
    }
  };

  const revertPolish = () => {
    setPolishedText(null);
    setPolishSummary("");
    setPolishError(null);
    setSmartApplyResidual([]);
    setFinalAuditResult(null);
    setAuditError(null);
    setAppliedAuditFindings(new Set());
  };

  /** Apply a single audit finding's ``replacement`` to the current body
   *  text. Splices the replacement in for the first occurrence of
   *  ``location_quote``. Empty replacement = delete + tidy whitespace.
   *  No-ops if the finding is already applied or has no replacement. */
  const applyAuditFinding = (index: number) => {
    if (!finalAuditResult) return;
    if (appliedAuditFindings.has(index)) return;
    const finding = finalAuditResult.findings[index];
    if (!finding || typeof finding.replacement !== "string") return;
    const baseText = polishedText ?? result?.input_text ?? "";
    if (!baseText) return;
    const idx = baseText.indexOf(finding.location_quote);
    if (idx < 0) {
      // Quote not in the current text - probably because an earlier
      // apply changed the surrounding context. Mark the finding as
      // applied anyway so the user can move on; they'll see the
      // strike-through and know it's not actionable on this version.
      setAppliedAuditFindings((prev) => new Set(prev).add(index));
      return;
    }
    const before = baseText.slice(0, idx);
    const after = baseText.slice(idx + finding.location_quote.length);
    let next = before + finding.replacement + after;
    // Clean up double-spaces + orphan punctuation introduced by an
    // empty replacement (= delete).
    if (finding.replacement === "") {
      next = next.replace(/  +/g, " ").replace(/\s+([.,;:!?])/g, "$1");
      // Two empty paragraphs collapsing into three newlines -> two.
      next = next.replace(/\n{3,}/g, "\n\n");
    }
    setPolishedText(next);
    setAppliedAuditFindings((prev) => new Set(prev).add(index));
  };

  /** "Audit-Befunde komplett umsetzen lassen": one LLM call (Sonnet)
   *  that rewrites the whole text addressing every finding. Distinct
   *  from the deterministic per-finding splice — handles findings
   *  without a clean replacement (e.g. "restructure this section"),
   *  and produces one coherent rewrite instead of N independent
   *  splices that might leave gaps. */
  const applyAllAuditByLLM = async () => {
    if (!finalAuditResult || isApplyingAuditByLLM) return;
    if (finalAuditResult.findings.length === 0) return;
    const baseText = polishedText ?? result?.input_text ?? "";
    if (!baseText) return;
    setIsApplyingAuditByLLM(true);
    setApplyAuditByLLMError(null);
    try {
      const out = await applyAuditFindings(baseText, finalAuditResult.findings);
      if (out.rewritten_text && out.rewritten_text.trim()) {
        setPolishedText(out.rewritten_text);
        setPolishSummary(
          `${out.findings_applied} Audit-Befunde von Claude umgesetzt.`,
        );
        // Treat every finding as applied - the rewrite covered them.
        setAppliedAuditFindings(
          new Set(finalAuditResult.findings.map((_, i) => i)),
        );
      }
    } catch (err) {
      if (err instanceof AnalysisError) {
        setApplyAuditByLLMError(err.message);
      } else if (err instanceof Error) {
        setApplyAuditByLLMError(err.message);
      } else {
        setApplyAuditByLLMError("Übernahme der Audit-Befunde fehlgeschlagen.");
      }
    } finally {
      setIsApplyingAuditByLLM(false);
    }
  };

  /** One-click "fix everything that's actionable + urgent". Iterates
   *  critical + high findings in order, applying each replacement to
   *  the running text. Lower-severity findings stay in the panel for
   *  manual review. */
  const applyAllUrgentAuditFindings = () => {
    if (!finalAuditResult) return;
    const baseText = polishedText ?? result?.input_text ?? "";
    if (!baseText) return;
    let working = baseText;
    const newlyApplied = new Set(appliedAuditFindings);
    finalAuditResult.findings.forEach((finding, index) => {
      if (newlyApplied.has(index)) return;
      if (finding.severity !== "critical" && finding.severity !== "high") return;
      if (typeof finding.replacement !== "string") return;
      const idx = working.indexOf(finding.location_quote);
      if (idx < 0) {
        // Earlier apply changed the surrounding context. Mark it
        // applied so it disappears from the actionable list.
        newlyApplied.add(index);
        return;
      }
      const before = working.slice(0, idx);
      const after = working.slice(idx + finding.location_quote.length);
      working = before + finding.replacement + after;
      if (finding.replacement === "") {
        working = working
          .replace(/  +/g, " ")
          .replace(/\s+([.,;:!?])/g, "$1")
          .replace(/\n{3,}/g, "\n\n");
      }
      newlyApplied.add(index);
    });
    setPolishedText(working);
    setAppliedAuditFindings(newlyApplied);
  };

  /** Trigger the holistic Opus-4.7 compliance audit over the *current*
   *  body text (polished/smart-applied version if present, otherwise
   *  the original input). Captures structural issues the per-claim
   *  pipeline can't see: broken tables, topic drift, duplicates,
   *  factual errors, UWG/HWG risks, context-induced claims. */
  const triggerFinalAudit = async () => {
    if (!result || isAuditing) return;
    const text = polishedText ?? result.input_text;
    if (!text.trim()) return;
    setIsAuditing(true);
    setAuditError(null);
    try {
      const audit = await runFinalAudit(text, {
        reformulatedFromOriginal: polishedText !== null,
      });
      setFinalAuditResult(audit);
      // Fresh audit -> fresh applied-set. Old applies are no longer
      // meaningful because the finding indices change.
      setAppliedAuditFindings(new Set());
    } catch (err) {
      if (err instanceof AnalysisError) {
        setAuditError(err.message);
      } else if (err instanceof Error) {
        setAuditError(err.message);
      } else {
        setAuditError("Finaler Compliance-Check fehlgeschlagen.");
      }
    } finally {
      setIsAuditing(false);
    }
  };

  const onPdfExtracted = (text: string, sourceReference: string) => {
    setInput(text);
    setPdfFilename(sourceReference);
    setSourceUrl(null);
    setActiveTab("text");
  };

  const onUrlExtracted = (text: string, sourceReference: string) => {
    setInput(text);
    setSourceUrl(sourceReference);
    setPdfFilename(null);
    setActiveTab("text");
  };

  const length = input.length;
  const tooShort = input.trim().length < MIN_CHARS;
  const tooLong = length > MAX_CHARS;
  const warnLength = length >= MAX_CHARS * WARN_THRESHOLD && !tooLong;
  const runDisabled = tooShort || tooLong;

  const counts = useMemo(() => {
    if (!result) return null;
    const evals = result.evaluated_claims;
    return {
      total: result.detected_claims.length,
      evaluated: evals.length,
      allowed: evals.filter((c) => c.status === "allowed").length,
      borderline: evals.filter((c) => c.status === "borderline").length,
      forbidden: evals.filter((c) => c.status === "forbidden").length,
      unclear: evals.filter((c) => c.status === "unclear").length,
    };
  }, [result]);

  const applicableClaims = useMemo(() => {
    if (!result) return [];
    return result.evaluated_claims.filter(
      (c) =>
        c.rewrite_suggestion &&
        (c.status === "borderline" || c.status === "forbidden"),
    );
  }, [result]);

  const editedText = useMemo(() => {
    if (!result || appliedIds.size === 0) return null;
    return applyRewritesToText(
      result.input_text,
      result.evaluated_claims,
      appliedIds,
    );
  }, [result, appliedIds]);

  const handleClaimClick = (claimId: string) => {
    setActiveClaimId(claimId);
    const el = document.getElementById(`claim-${claimId}`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const applyClaim = (claimId: string) => {
    setAppliedIds((prev) => new Set(prev).add(claimId));
    setActiveClaimId(claimId);
  };

  const revertClaim = (claimId: string) => {
    setAppliedIds((prev) => {
      const next = new Set(prev);
      next.delete(claimId);
      return next;
    });
  };

  const applyAll = () => {
    setAppliedIds(new Set(applicableClaims.map((c) => c.id)));
  };

  const revertAll = () => {
    setAppliedIds(new Set());
  };

  /** Ask Claude to (a) fill in any missing rewrite suggestions, then
   *  (b) rewrite the whole text *paragraph by paragraph* so the
   *  reformulations are organically woven into the surrounding
   *  sentences instead of spliced in as 1:1 replacements.
   *
   *  Result lands in ``polishedText``: the same view layer that the
   *  Polish button already uses. The user sees the cleaned, in-context
   *  rewrite directly, with a "Rückgängig" option. */
  const rewriteAll = async () => {
    if (!result || isRewritingAll) return;
    const targets = result.evaluated_claims.filter(
      (c) => c.status !== "allowed",
    );
    if (targets.length === 0) return;

    setIsRewritingAll(true);
    setRewriteAllError(null);
    try {
      // Step 1: ensure every problematic claim has a rewrite suggestion.
      const rewrites = await rewriteAllClaims(targets, result.input_text);
      const merged = result.evaluated_claims.map((c) =>
        rewrites[c.id]
          ? { ...c, rewrite_suggestion: rewrites[c.id] }
          : c,
      );
      setResult({ ...result, evaluated_claims: merged });
      setAppliedIds(
        new Set(
          merged
            .filter(
              (c) =>
                c.rewrite_suggestion &&
                c.status !== "allowed",
            )
            .map((c) => c.id),
        ),
      );

      // Step 2: paragraph-aware rewrite of the full text. Sonnet sees
      // each paragraph + the claim list that touches it, and produces
      // a clean marketing-grade rewrite. Replaces the naive string-
      // splice that was producing nonsense like
      // `"Vitamin D trägt zu …"` mid-sentence.
      const smartApply = await smartApplyClaims(merged, result.input_text);
      const rewrittenText = smartApply.rewritten_text;
      if (rewrittenText && rewrittenText.trim()) {
        setPolishedText(rewrittenText);
        const residualCount = smartApply.residual_claims.length;
        if (residualCount > 0) {
          setPolishSummary(
            `Absatzweise neu geschrieben. Konvergenz-Check: ${residualCount} ${
              residualCount === 1 ? "Claim" : "Claims"
            } verbleibt — bitte manuell prüfen.`,
          );
        } else if (smartApply.convergence_warning) {
          setPolishSummary(
            `Absatzweise neu geschrieben. ${smartApply.convergence_warning}`,
          );
        } else {
          setPolishSummary(
            "Absatzweise neu geschrieben — keine Claims mehr erkannt.",
          );
        }
        setSmartApplyResidual(smartApply.residual_claims);
      }
    } catch (err) {
      if (err instanceof AnalysisError) {
        setRewriteAllError(err.message);
      } else if (err instanceof Error) {
        setRewriteAllError(err.message);
      } else {
        setRewriteAllError("Reformulierung fehlgeschlagen.");
      }
    } finally {
      setIsRewritingAll(false);
    }
  };

  const copyEditedText = async () => {
    const text = editedText ?? result?.input_text;
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopyHint(true);
    window.setTimeout(() => setCopyHint(false), 2000);
  };

  const recheckEditedText = () => {
    if (!editedText) return;
    setInput(editedText);
    void runAnalysis(editedText);
  };

  return (
    <>
      <AppHeader
        crumbs={[{ label: "Workspace" }, { label: "Neue Prüfung" }]}
      />

      <div className="flex-1 px-6 py-8 lg:px-10">
        <div className="flex flex-col gap-8">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h1 className="font-serif text-3xl leading-tight tracking-tight">
                Neue Prüfung
              </h1>
              <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
                Füge Werbetext, Produktseiten-URL oder PDF ein – ClaimGuard
                erkennt und bewertet jeden Health Claim.
              </p>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link href="/app/history/chk_2k9f3a">
                <Download className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                Beispielreport
              </Link>
            </Button>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <KpiCard
              label="Prüfungen diesen Monat"
              value={KPIS.analysesThisMonth.value.toString()}
              delta={KPIS.analysesThisMonth.delta}
              deltaTone="positive"
              icon={Activity}
            />
            <KpiCard
              label="Ø Compliance-Score"
              value={`${KPIS.averageScore.value} %`}
              delta={KPIS.averageScore.delta}
              deltaTone="positive"
              icon={TrendingUp}
            />
            <KpiCard
              label="Verhinderte Risiko-Claims"
              value={KPIS.preventedRisks.value.toString()}
              sublabel={KPIS.preventedRisks.window}
              icon={ShieldCheck}
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* LEFT: Editor or HighlightedText */}
            <div className="flex flex-col rounded-xl border border-border/70 bg-card shadow-sm">
              <div className="flex items-center justify-between border-b border-border/60 px-4 py-3">
                <div className="flex items-center gap-1 rounded-md bg-muted/60 p-0.5">
                  {TABS.map((tab) => {
                    const Icon = tab.icon;
                    const active = activeTab === tab.id;
                    const disabled =
                      phase === "running" || phase === "done";
                    return (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => setActiveTab(tab.id)}
                        disabled={disabled}
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors",
                          active
                            ? "bg-background text-foreground shadow-sm"
                            : "text-muted-foreground hover:text-foreground",
                          disabled && "cursor-not-allowed opacity-60",
                        )}
                      >
                        <Icon className="h-3 w-3" aria-hidden />
                        {tab.label}
                      </button>
                    );
                  })}
                </div>

                <div className="flex items-center gap-2">
                  {phase === "done" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={resetAnalysis}
                      className="h-7 px-2 text-xs"
                    >
                      <Pencil className="mr-1 h-3 w-3" aria-hidden />
                      Bearbeiten
                    </Button>
                  )}
                  <span className="inline-flex items-center gap-1 rounded-md bg-muted/60 px-2 py-1 text-xs text-muted-foreground">
                    Lebensmittel / Supplement
                  </span>
                  <button
                    type="button"
                    aria-label="Optionen"
                    className="grid h-7 w-7 place-items-center rounded text-muted-foreground hover:bg-muted"
                  >
                    <MoreHorizontal className="h-3.5 w-3.5" aria-hidden />
                  </button>
                </div>
              </div>

              {phase === "done" && result ? (
                <div className="flex flex-1 flex-col">
                  {polishedText ? (
                    <PolishedView
                      text={polishedText}
                      summary={polishSummary}
                      onRevert={revertPolish}
                    />
                  ) : (
                    <>
                      {appliedIds.size > 0 && (
                        <div className="mx-5 mt-5 inline-flex w-fit items-center gap-1.5 rounded-full bg-status-allowed-bg px-2.5 py-1 text-[11px] font-medium text-status-allowed">
                          <CheckCheck className="h-3 w-3" aria-hidden />
                          {appliedIds.size} Reformulierung
                          {appliedIds.size > 1 ? "en" : ""} übernommen — bearbeitete Version
                        </div>
                      )}
                      <HighlightedText
                        text={result.input_text}
                        detectedClaims={result.detected_claims}
                        evaluatedClaims={result.evaluated_claims}
                        onClaimClick={handleClaimClick}
                        activeClaimId={activeClaimId}
                        appliedIds={appliedIds}
                      />
                    </>
                  )}
                </div>
              ) : (
                <>
                  {activeTab === "text" && (
                    <div className="flex-1">
                      <MarkdownEditor
                        value={input}
                        onChange={(md) => setInput(md.slice(0, MAX_CHARS))}
                        disabled={phase === "running"}
                      />
                    </div>
                  )}
                  {activeTab === "url" && (
                    <UrlInput
                      onExtracted={onUrlExtracted}
                      disabled={phase === "running"}
                    />
                  )}
                  {activeTab === "pdf" && (
                    <PdfDropzone
                      onExtracted={onPdfExtracted}
                      disabled={phase === "running"}
                    />
                  )}
                </>
              )}

              <div className="flex items-center justify-between border-t border-border/60 px-4 py-3 text-xs text-muted-foreground">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 tabular-nums",
                      warnLength && "text-status-borderline",
                      tooLong && "font-semibold text-status-forbidden",
                    )}
                  >
                    {warnLength && (
                      <TriangleAlert className="h-3 w-3" aria-hidden />
                    )}
                    {(editedText ?? input).length.toLocaleString("de-DE")} /{" "}
                    {MAX_CHARS.toLocaleString("de-DE")} Zeichen
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Sparkles className="h-3 w-3" aria-hidden />
                    Sonnet 4.6
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Check className="h-3 w-3 text-primary" aria-hidden />
                    Zero-Retention
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {phase === "done" && editedText ? (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={copyEditedText}
                      >
                        <Clipboard className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                        {copyHint ? "Kopiert!" : "Text kopieren"}
                      </Button>
                      <Button size="sm" onClick={recheckEditedText}>
                        <RefreshCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                        Erneut prüfen
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={resetAnalysis}
                        disabled={phase === "running"}
                      >
                        <RefreshCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                        Zurücksetzen
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => runAnalysis()}
                        disabled={runDisabled || phase === "running" || phase === "done"}
                      >
                        <Scan className="mr-1.5 h-3.5 w-3.5" aria-hidden />
                        Claims prüfen
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* RIGHT: Result panel */}
            <div className="flex flex-col rounded-xl border border-border/70 bg-card shadow-sm">
              <div className="flex items-center justify-between border-b border-border/60 px-5 py-3">
                <h2 className="text-sm font-medium">Ergebnisse</h2>
                {phase === "done" && result && (
                  <span
                    className="font-mono text-[11px] text-muted-foreground"
                    title="Obergrenze – mit aktivem Prompt-Caching liegt die echte Anthropic-Rechnung in der Regel deutlich darunter."
                  >
                    {(result.latency_ms / 1000).toFixed(1)} s ·{" "}
                    {result.input_tokens.toLocaleString("de-DE")}/
                    {result.output_tokens.toLocaleString("de-DE")} Tokens · ≤ ${" "}
                    {result.estimated_cost_usd.toFixed(2)}
                  </span>
                )}
              </div>

              {phase === "idle" && <IdleState />}
              {phase === "running" && (
                <RunningState currentStep={currentStep} />
              )}
              {phase === "error" && (
                <ErrorState message={error} onReset={resetAnalysis} />
              )}
              {phase === "done" && result && counts && (
                <DoneState
                  result={result}
                  counts={counts}
                  applicableClaims={applicableClaims}
                  appliedIds={appliedIds}
                  activeClaimId={activeClaimId}
                  onSelectClaim={handleClaimClick}
                  onApplyClaim={applyClaim}
                  onRevertClaim={revertClaim}
                  onApplyAll={applyAll}
                  onRevertAll={revertAll}
                  onRewriteAll={() => void rewriteAll()}
                  isRewritingAll={isRewritingAll}
                  rewriteAllError={rewriteAllError}
                  onPolish={() => void polish()}
                  isPolishing={isPolishing}
                  polishError={polishError}
                  polishedText={polishedText}
                  smartApplyResidual={smartApplyResidual}
                  finalAuditResult={finalAuditResult}
                  isAuditing={isAuditing}
                  auditError={auditError}
                  onRunAudit={() => void triggerFinalAudit()}
                  onResetAudit={() => {
                    setFinalAuditResult(null);
                    setAuditError(null);
                    setAppliedAuditFindings(new Set());
                  }}
                  appliedAuditFindings={appliedAuditFindings}
                  onApplyAuditFinding={applyAuditFinding}
                  onApplyAllUrgentAudit={applyAllUrgentAuditFindings}
                  onApplyAllAuditByLLM={() => void applyAllAuditByLLM()}
                  isApplyingAuditByLLM={isApplyingAuditByLLM}
                  applyAuditByLLMError={applyAuditByLLMError}
                />
              )}
            </div>
          </div>

          <p className="max-w-3xl text-xs text-muted-foreground">
            <strong className="font-semibold text-foreground">Stufe 2 (KI-Schätzung):</strong>{" "}
            Detection und Bewertung laufen live gegen Claude Sonnet 4.6. Die genannten
            Rechtsgrundlagen sind <strong>nicht aus einer kuratierten Quellen-Datenbank</strong>{" "}
            zitiert – Aktenzeichen sollten gegengeprüft werden. Mit Stufe 3 (PROJ-9 Retrieval +
            PROJ-10 Opus-Evaluation) folgen verifizierte Zitate.
          </p>
        </div>
      </div>
    </>
  );
}

function IdleState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-10 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-full bg-accent text-accent-foreground">
        <Sparkles className="h-5 w-5" aria-hidden />
      </span>
      <div>
        <h3 className="font-serif text-lg font-semibold tracking-tight">
          Bereit zur Analyse
        </h3>
        <p className="mt-1 max-w-xs text-sm text-muted-foreground">
          Klick „Claims prüfen" – Sonnet 4.6 erkennt und bewertet alle Health
          Claims im Text.
        </p>
      </div>
    </div>
  );
}

function RunningState({ currentStep }: { currentStep: number }) {
  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Analyse läuft
        </div>
        <div className="mt-1 font-serif text-lg font-semibold tracking-tight">
          Schritt {Math.min(currentStep + 1, PIPELINE_STEPS.length)} von{" "}
          {PIPELINE_STEPS.length}
        </div>
      </div>
      <AnalysisProgress currentStep={currentStep} />
      <p className="mt-auto text-[11px] text-muted-foreground">
        Detection in 2-6 s, Bewertung läuft parallel pro Claim.
      </p>
    </div>
  );
}

function ErrorState({
  message,
  onReset,
}: {
  message: string | null;
  onReset: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-full bg-status-forbidden-bg text-status-forbidden">
        <AlertCircle className="h-5 w-5" aria-hidden />
      </span>
      <div>
        <h3 className="font-serif text-lg font-semibold tracking-tight">
          Analyse fehlgeschlagen
        </h3>
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          {message ?? "Unbekannter Fehler."}
        </p>
      </div>
      <Button variant="outline" size="sm" onClick={onReset}>
        <RefreshCcw className="mr-1.5 h-3.5 w-3.5" aria-hidden />
        Erneut versuchen
      </Button>
    </div>
  );
}

/** Cleaned final view shown after a successful Polish pass. No
 *  highlights here - the position indices from detection no longer line
 *  up with the polished text, and the user is past the verification
 *  phase anyway. */
function PolishedView({
  text,
  summary,
  onRevert,
}: {
  text: string;
  summary: string;
  onRevert: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col">
      <div className="mx-5 mt-5 flex flex-wrap items-center justify-between gap-2 rounded-md border border-status-allowed/30 bg-status-allowed-bg/40 px-3 py-2 text-xs text-status-allowed">
        <span className="inline-flex items-center gap-1.5 font-medium">
          <Sparkles className="h-3 w-3" aria-hidden />
          Schluss-Korrektur angewandt
          {summary && <span className="font-normal text-foreground/70">— {summary}</span>}
        </span>
        <button
          type="button"
          onClick={onRevert}
          className="inline-flex items-center gap-1 rounded text-[11px] font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <RotateCcw className="h-3 w-3" aria-hidden />
          Rückgängig
        </button>
      </div>
      <div className="prose prose-sm max-w-none overflow-y-auto px-5 py-5 font-serif text-[15px] leading-[1.85] text-foreground prose-headings:font-serif prose-headings:tracking-tight prose-headings:text-foreground prose-strong:text-foreground prose-a:text-primary prose-li:my-1">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </div>
    </div>
  );
}

function DoneState({
  result,
  counts,
  applicableClaims,
  appliedIds,
  activeClaimId,
  onSelectClaim,
  onApplyClaim,
  onRevertClaim,
  onApplyAll,
  onRevertAll,
  onRewriteAll,
  isRewritingAll,
  rewriteAllError,
  onPolish,
  isPolishing,
  polishError,
  polishedText,
  smartApplyResidual,
  finalAuditResult,
  isAuditing,
  auditError,
  onRunAudit,
  onResetAudit,
  appliedAuditFindings,
  onApplyAuditFinding,
  onApplyAllUrgentAudit,
  onApplyAllAuditByLLM,
  isApplyingAuditByLLM,
  applyAuditByLLMError,
}: {
  result: AnalysisResponse;
  counts: {
    total: number;
    evaluated: number;
    allowed: number;
    borderline: number;
    forbidden: number;
    unclear: number;
  };
  applicableClaims: EvaluatedClaim[];
  appliedIds: Set<string>;
  activeClaimId: string | null;
  onSelectClaim: (id: string) => void;
  onApplyClaim: (id: string) => void;
  onRevertClaim: (id: string) => void;
  onApplyAll: () => void;
  onRevertAll: () => void;
  onRewriteAll: () => void;
  isRewritingAll: boolean;
  rewriteAllError: string | null;
  onPolish: () => void;
  isPolishing: boolean;
  polishError: string | null;
  polishedText: string | null;
  smartApplyResidual: DetectedClaim[];
  finalAuditResult: FinalAuditResult | null;
  isAuditing: boolean;
  auditError: string | null;
  onRunAudit: () => void;
  onResetAudit: () => void;
  appliedAuditFindings: Set<number>;
  onApplyAuditFinding: (index: number) => void;
  onApplyAllUrgentAudit: () => void;
  onApplyAllAuditByLLM: () => void;
  isApplyingAuditByLLM: boolean;
  applyAuditByLLMError: string | null;
}) {
  const detectedNotEvaluated = result.detected_claims.filter(
    (d) => !result.evaluated_claims.some((e) => e.id === d.id),
  );
  const totalApplicable = applicableClaims.length;
  const allApplied = totalApplicable > 0 && appliedIds.size === totalApplicable;

  const exportPdf = () => {
    const today = new Date().toISOString().slice(0, 10);
    const shortId = result.id.slice(0, 8);
    const previousTitle = document.title;
    document.title = `ClaimGuard-Report-${shortId}-${today}`;
    try {
      window.print();
    } finally {
      document.title = previousTitle;
    }
  };

  const exportDoc = async () => {
    const today = new Date().toISOString().slice(0, 10);
    const shortId = result.id.slice(0, 8);
    const text = polishedText
      ? polishedText
      : applyRewritesToText(
          result.input_text,
          result.evaluated_claims,
          appliedIds,
        );
    const suffix = polishedText
      ? "-final"
      : appliedIds.size > 0
        ? "-bearbeitet"
        : "";
    await downloadAsDoc(text, `ClaimGuard-${shortId}-${today}${suffix}`);
  };

  return (
    <div data-print="report" className="flex-1 space-y-3 overflow-y-auto p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-serif text-lg font-semibold tracking-tight">
            ClaimGuard-Analysebericht
          </h2>
          <p className="text-xs text-muted-foreground">
            ID {result.id.slice(0, 8)} · {new Date(result.created_at).toLocaleString("de-DE")}
            {result.source_reference && ` · Quelle: ${result.source_reference}`}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => void exportDoc()}>
            <FileText className="mr-1.5 h-3.5 w-3.5" aria-hidden />
            Als Word speichern
          </Button>
          <Button variant="outline" size="sm" onClick={exportPdf}>
            <Download className="mr-1.5 h-3.5 w-3.5" aria-hidden />
            Als PDF speichern
          </Button>
        </div>
      </div>

      <div
        data-print="disclaimer"
        className="hidden rounded-md border border-border/60 bg-card px-4 py-3 text-xs leading-relaxed text-foreground print:block"
      >
        <strong>Wichtig:</strong> Diese Analyse ist eine automatisierte Vorabprüfung
        gesundheitsbezogener Werbeaussagen nach VO (EG) 1924/2006 und ist
        <strong> kein Ersatz für Rechtsberatung</strong>. ClaimGuard haftet nicht
        für geschäftliche Entscheidungen auf Basis dieser Auswertung.
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-accent/50 bg-accent/30 px-3 py-2 text-xs">
        <Info className="h-3.5 w-3.5 shrink-0 text-accent-foreground" aria-hidden />
        <span className="text-foreground/85">
          <strong className="font-semibold">{counts.total} Claims erkannt,</strong>{" "}
          {counts.evaluated} bewertet
          {counts.evaluated > 0 && (
            <>
              {" "}
              · <span className="text-status-allowed">{counts.allowed} konform</span>
              {" / "}
              <span className="text-status-borderline">{counts.borderline} Risiko</span>
              {" / "}
              <span className="text-status-forbidden">{counts.forbidden} unzulässig</span>
              {counts.unclear > 0 && (
                <>
                  {" / "}
                  <span className="text-status-unclear">{counts.unclear} unklar</span>
                </>
              )}
            </>
          )}
        </span>
      </div>

      {appliedIds.size > 0 && !polishedText && (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-status-allowed/30 bg-status-allowed-bg/30 px-3 py-2 text-xs">
            <span className="text-foreground/85">
              Reformulierungen sind übernommen — eine Schluss-Korrektur glättet
              jetzt Grammatik und Übergänge, ohne den rechtlichen Inhalt
              anzufassen.
            </span>
            <button
              type="button"
              onClick={onPolish}
              disabled={isPolishing}
              className="inline-flex items-center gap-1 rounded bg-status-allowed/90 px-2.5 py-1 text-[11px] font-semibold text-white transition-colors hover:bg-status-allowed disabled:opacity-60"
            >
              {isPolishing ? (
                <>
                  <Sparkles className="h-3 w-3 animate-pulse" aria-hidden />
                  Schluss-Korrektur läuft …
                </>
              ) : (
                <>
                  <Sparkles className="h-3 w-3" aria-hidden />
                  Final glätten
                </>
              )}
            </button>
          </div>
          {polishError && (
            <div className="flex items-start gap-2 rounded-md border border-status-forbidden/30 bg-status-forbidden-bg/40 px-3 py-2 text-xs text-status-forbidden">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
              <span>{polishError}</span>
            </div>
          )}
        </div>
      )}

      {(() => {
        const problematic = result.evaluated_claims.filter(
          (c) => c.status !== "allowed",
        );
        if (problematic.length === 0) return null;
        const missingRewrites = problematic.filter(
          (c) => !c.rewrite_suggestion,
        ).length;
        return (
          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2 text-xs">
              <span className="text-foreground/85">
                {totalApplicable > 0 ? (
                  <>
                    <strong className="font-semibold tabular-nums">
                      {appliedIds.size} / {totalApplicable}
                    </strong>{" "}
                    Reformulierungen übernommen
                  </>
                ) : (
                  <>
                    {problematic.length}{" "}
                    {problematic.length === 1 ? "Claim braucht" : "Claims brauchen"}{" "}
                    Reformulierung — Claude kann sie automatisch erstellen.
                  </>
                )}
              </span>
              <div className="flex flex-wrap items-center gap-1.5">
                {appliedIds.size > 0 && (
                  <button
                    type="button"
                    onClick={onRevertAll}
                    disabled={isRewritingAll}
                    className="inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
                  >
                    <RotateCcw className="h-3 w-3" aria-hidden />
                    Alle zurücksetzen
                  </button>
                )}
                {totalApplicable > 0 && !allApplied && (
                  <button
                    type="button"
                    onClick={onApplyAll}
                    disabled={isRewritingAll}
                    className="inline-flex items-center gap-1 rounded bg-primary/80 px-2.5 py-1 text-[11px] font-semibold text-primary-foreground transition-colors hover:bg-primary disabled:opacity-50"
                  >
                    <CheckCheck className="h-3 w-3" aria-hidden />
                    Vorschläge übernehmen
                  </button>
                )}
                <button
                  type="button"
                  onClick={onRewriteAll}
                  disabled={isRewritingAll}
                  title={
                    missingRewrites > 0
                      ? `Claude schreibt ${missingRewrites} fehlende Reformulierungen und übernimmt alle.`
                      : "Alle Reformulierungen übernehmen."
                  }
                  className="inline-flex items-center gap-1 rounded bg-primary px-2.5 py-1 text-[11px] font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
                >
                  {isRewritingAll ? (
                    <>
                      <Sparkles className="h-3 w-3 animate-pulse" aria-hidden />
                      Claude schreibt …
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3 w-3" aria-hidden />
                      {missingRewrites > 0
                        ? "Claude alles umschreiben & übernehmen"
                        : "Alle automatisch übernehmen"}
                    </>
                  )}
                </button>
              </div>
            </div>
            {rewriteAllError && (
              <div className="flex items-start gap-2 rounded-md border border-status-forbidden/30 bg-status-forbidden-bg/40 px-3 py-2 text-xs text-status-forbidden">
                <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                <span>{rewriteAllError}</span>
              </div>
            )}
          </div>
        );
      })()}

      {result.evaluated_claims.map((claim, i) => (
        <EvaluatedClaimCard
          key={claim.id}
          claim={claim}
          index={i + 1}
          isActive={activeClaimId === claim.id}
          isApplied={appliedIds.has(claim.id)}
          onSelect={() => onSelectClaim(claim.id)}
          onApply={
            claim.rewrite_suggestion &&
            (claim.status === "borderline" || claim.status === "forbidden")
              ? () => onApplyClaim(claim.id)
              : undefined
          }
          onRevert={() => onRevertClaim(claim.id)}
        />
      ))}

      {detectedNotEvaluated.length > 0 && (
        <div className="space-y-3">
          <div className="rounded-lg border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground">
            {detectedNotEvaluated.length} Claim(s) wurden erkannt, aber nicht
            bewertet – Schema-Fehler bei der Bewertung. Detection-Daten:
          </div>
          {detectedNotEvaluated.map((claim) => (
            <DetectionClaimCard key={claim.id} claim={claim} />
          ))}
        </div>
      )}

      {result.warnings.map((w, i) => (
        <div
          key={i}
          className="rounded-lg border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground"
        >
          {w}
        </div>
      ))}

      {smartApplyResidual.length > 0 && (
        <div className="rounded-lg border border-status-borderline/40 bg-status-borderline-bg/30 p-3 text-xs">
          <div className="flex items-start gap-2">
            <AlertCircle
              className="mt-0.5 h-3.5 w-3.5 shrink-0 text-status-borderline"
              aria-hidden
            />
            <div className="space-y-1">
              <div className="font-medium text-status-borderline">
                Konvergenz-Check: {smartApplyResidual.length}{" "}
                {smartApplyResidual.length === 1 ? "Claim" : "Claims"} im
                umgeschriebenen Text noch erkannt
              </div>
              <div className="text-foreground/75">
                Die automatische Reformulierung hat noch nicht alle Probleme
                gelöst. Bitte den finalen Compliance-Check unten ausführen
                oder die markierten Stellen manuell prüfen.
              </div>
            </div>
          </div>
        </div>
      )}

      <FinalAuditPanel
        result={finalAuditResult}
        isAuditing={isAuditing}
        error={auditError}
        onRun={onRunAudit}
        onReset={onResetAudit}
        onApplyFinding={onApplyAuditFinding}
        onApplyAllCriticalHigh={onApplyAllUrgentAudit}
        appliedFindings={appliedAuditFindings}
        onApplyAllByLLM={onApplyAllAuditByLLM}
        isApplyingAllByLLM={isApplyingAuditByLLM}
        applyAllByLLMError={applyAuditByLLMError}
      />
    </div>
  );
}
