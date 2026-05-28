export type ClaimType =
  | "nutrient_based"
  | "health_based"
  | "reduction_based"
  | "wellbeing_based"
  | "disease_based";

export type Implicitness = "explicit" | "implicit";

export type DetectedClaim = {
  id: string;
  claim_text: string;
  claim_type: ClaimType;
  nutrient: string | null;
  substance: string | null;
  implicitness: Implicitness;
  position_start: number;
  position_end: number;
};

export type EvaluationStatus = "allowed" | "borderline" | "forbidden" | "unclear";
export type RiskLevel = "low" | "medium" | "high";

export type LegalHint = {
  reference: string;
  rationale: string;
  verified: boolean;
  chunk_id: string | null;
  url: string | null;
};

export type RetrievalSourceType = "eu_claim" | "regulation" | "case_law" | "botanical";

export type RetrievalHit = {
  chunk_id: string;
  source_type: RetrievalSourceType;
  score: number;
  snippet: string;
  reference: string;
  url: string;
  metadata: Record<string, string | number | null>;
};

export type EvaluatedClaim = DetectedClaim & {
  status: EvaluationStatus;
  confidence: number;
  risk_level: RiskLevel;
  reasoning: string;
  rewrite_suggestion: string | null;
  legal_hints: LegalHint[];
  evidence: RetrievalHit[];
  evaluation_model: string;
  evaluation_prompt_version: string;
};

export type AnalysisResponse = {
  id: string;
  status: "completed";
  source_type: "text" | "url" | "pdf";
  source_reference: string | null;
  input_text: string;
  detected_claims: DetectedClaim[];
  evaluated_claims: EvaluatedClaim[];
  prompt_version: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  latency_ms: number;
  created_at: string;
  warnings: string[];
};

export type AnalysisRequest = {
  source_type?: "text" | "url" | "pdf";
  source_reference?: string | null;
  input_text: string;
};

export type PdfExtractResponse = {
  text: string;
  page_count: number;
  char_count: number;
  source_reference: string;
};

export type UrlExtractResponse = {
  text: string;
  title: string | null;
  final_url: string;
  char_count: number;
  source_reference: string;
};

export class AnalysisError extends Error {
  constructor(
    message: string,
    public code: string,
    public status: number,
  ) {
    super(message);
  }
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Build the request headers for every API call. If the user is logged
// in we attach the Supabase access token so the backend can resolve
// the request to ``CurrentUser`` once endpoints flip on auth gating
// (PROJ-1 frontend lands first, gating commit follows).
async function authHeaders(extra?: HeadersInit): Promise<HeadersInit> {
  const base: Record<string, string> = { "content-type": "application/json" };
  try {
    // Import is lazy so this module stays usable in environments where
    // the Supabase client isn't initialised (e.g. unit tests).
    const { supabase } = await import("@/lib/supabase");
    if (supabase) {
      const { data } = await supabase.auth.getSession();
      const token = data.session?.access_token;
      if (token) base["authorization"] = `Bearer ${token}`;
    }
  } catch {
    // Supabase env not configured (local dev without keys) - send the
    // request anyway. The backend treats anonymous requests fine for
    // endpoints that don't require auth.
  }
  return { ...base, ...(extra as Record<string, string> | undefined) };
}

export async function createAnalysis(
  payload: AnalysisRequest,
): Promise<AnalysisResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/analyses`, {
      method: "POST",
      headers: await authHeaders(),
      body: JSON.stringify({ source_type: "text", ...payload }),
    });
  } catch (err) {
    // "Failed to fetch" from the browser means the API didn't answer at all
    // (server not running, wrong port, network down, CORS rejected before the
    // response headers could be read).
    throw new AnalysisError(
      `Die ClaimGuard-API unter ${API_BASE} antwortet nicht. Läuft der Backend-Server? Starte ihn mit "pnpm dev:api".`,
      "api_unreachable",
      0,
    );
  }

  if (!response.ok) {
    let code = "internal_error";
    let message = `Analyse fehlgeschlagen (HTTP ${response.status}).`;
    try {
      const body = await response.json();
      const detail = body?.detail ?? body;
      if (detail?.code) code = detail.code;
      if (detail?.message) message = detail.message;
      else if (Array.isArray(body?.detail)) {
        const first = body.detail[0];
        if (first?.msg) message = first.msg;
      }
    } catch {
      // keep default message
    }
    throw new AnalysisError(message, code, response.status);
  }

  return (await response.json()) as AnalysisResponse;
}

export async function extractPdf(file: File): Promise<PdfExtractResponse> {
  const form = new FormData();
  form.append("file", file);

  let response: Response;
  try {
    // Don't set content-type — fetch needs to fill in the multipart
    // boundary itself. We only want the Authorization header.
    const headers = await authHeaders();
    const { ["content-type"]: _omit, ...rest } = headers as Record<string, string>;
    response = await fetch(`${API_BASE}/api/extract/pdf`, {
      method: "POST",
      headers: rest,
      body: form,
    });
  } catch {
    throw new AnalysisError(
      `Die ClaimGuard-API unter ${API_BASE} antwortet nicht. Läuft der Backend-Server?`,
      "api_unreachable",
      0,
    );
  }

  if (!response.ok) {
    let code = "pdf_invalid";
    let message = `PDF-Extraktion fehlgeschlagen (HTTP ${response.status}).`;
    try {
      const body = await response.json();
      const detail = body?.detail ?? body;
      if (detail?.code) code = detail.code;
      if (detail?.message) message = detail.message;
    } catch {
      // keep defaults
    }
    throw new AnalysisError(message, code, response.status);
  }

  return (await response.json()) as PdfExtractResponse;
}

export type RewriteBatchResponse = {
  rewrites: Record<string, string>;
};

// Special rewrite sentinel: the LLM signalled that no compliant rewrite
// is possible for this claim. The frontend renders these as a
// "Streichen-empfohlen"-card instead of a real rewrite suggestion.
export const DELETE_MARKER = "[DELETE]";

export function isDeleteMarker(value: string | null | undefined): boolean {
  return typeof value === "string" && value.trim().toUpperCase() === DELETE_MARKER;
}

export type PolishResponse = {
  polished_text: string;
  change_summary: string;
};

export type SmartApplyResponse = {
  rewritten_text: string;
  residual_claims: DetectedClaim[];
  convergence_warning: string | null;
};

export async function smartApplyClaims(
  claims: EvaluatedClaim[],
  inputText: string,
): Promise<SmartApplyResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/analyses/smart-apply`, {
      method: "POST",
      headers: await authHeaders(),
      body: JSON.stringify({ claims, input_text: inputText }),
    });
  } catch {
    throw new AnalysisError(
      `Die ClaimGuard-API unter ${API_BASE} antwortet nicht.`,
      "api_unreachable",
      0,
    );
  }
  if (!response.ok) {
    let code = "smart_apply_failed";
    let message = `Smart-Apply fehlgeschlagen (HTTP ${response.status}).`;
    try {
      const body = await response.json();
      const detail = body?.detail ?? body;
      if (detail?.code) code = detail.code;
      if (detail?.message) message = detail.message;
    } catch {
      // keep defaults
    }
    throw new AnalysisError(message, code, response.status);
  }
  const data = (await response.json()) as SmartApplyResponse;
  return {
    rewritten_text: data.rewritten_text ?? "",
    residual_claims: data.residual_claims ?? [],
    convergence_warning: data.convergence_warning ?? null,
  };
}

// -- Final Audit (Opus 4.7 holistic compliance review) ------------

export type AuditSeverity = "low" | "medium" | "high" | "critical";

export type AuditCategory =
  | "broken-table"
  | "broken-list"
  | "duplicate-paragraph"
  | "orphaned-sentence"
  | "topic-drift"
  | "answer-misses-question"
  | "factual-error"
  | "circular-content"
  | "implicit-claim-by-context"
  | "context-disease-link"
  | "uwg-comparative"
  | "uwg-misleading"
  | "hwg-violation"
  | "lazy-disclaimer"
  | "adaptogen-term"
  | "observation-bias"
  | "expert-endorsement"
  | "presentation-medicinal"
  | "pharma-vocab-dosage"
  | "other";

export type AuditFinding = {
  severity: AuditSeverity;
  category: AuditCategory;
  location_quote: string;
  finding: string;
  recommendation: string;
  // Concrete, machine-applicable fix text. The frontend can splice
  // this into the document on "Übernehmen". null means the finding
  // is not a single-shot text edit (e.g. "restructure this section").
  // Empty string means "delete the location_quote".
  replacement: string | null;
};

export type FinalAuditResult = {
  overall_assessment: string;
  shippable: boolean;
  findings: AuditFinding[];
  model: string;
  prompt_version: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
};

export type ApplyAuditResponse = {
  rewritten_text: string;
  findings_applied: number;
};

export async function applyAuditFindings(
  text: string,
  findings: AuditFinding[],
  overallAssessment: string = "",
): Promise<ApplyAuditResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/analyses/apply-audit`, {
      method: "POST",
      headers: await authHeaders(),
      body: JSON.stringify({
        text,
        findings,
        overall_assessment: overallAssessment,
      }),
    });
  } catch {
    throw new AnalysisError(
      `Die ClaimGuard-API unter ${API_BASE} antwortet nicht.`,
      "api_unreachable",
      0,
    );
  }
  if (!response.ok) {
    let code = "apply_audit_failed";
    let message = `Übernahme der Audit-Befunde fehlgeschlagen (HTTP ${response.status}).`;
    try {
      const body = await response.json();
      const detail = body?.detail ?? body;
      if (detail?.code) code = detail.code;
      if (detail?.message) message = detail.message;
    } catch {
      // keep defaults
    }
    throw new AnalysisError(message, code, response.status);
  }
  const data = (await response.json()) as ApplyAuditResponse;
  return {
    rewritten_text: data.rewritten_text ?? "",
    findings_applied: data.findings_applied ?? 0,
  };
}

export async function runFinalAudit(
  text: string,
  options: { reformulatedFromOriginal?: boolean } = {},
): Promise<FinalAuditResult> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/analyses/final-audit`, {
      method: "POST",
      headers: await authHeaders(),
      body: JSON.stringify({
        text,
        reformulated_from_original: options.reformulatedFromOriginal ?? false,
      }),
    });
  } catch {
    throw new AnalysisError(
      `Die ClaimGuard-API unter ${API_BASE} antwortet nicht.`,
      "api_unreachable",
      0,
    );
  }
  if (!response.ok) {
    let code = "final_audit_failed";
    let message = `Finaler Compliance-Check fehlgeschlagen (HTTP ${response.status}).`;
    try {
      const body = await response.json();
      const detail = body?.detail ?? body;
      if (detail?.code) code = detail.code;
      if (detail?.message) message = detail.message;
    } catch {
      // keep defaults
    }
    throw new AnalysisError(message, code, response.status);
  }
  return (await response.json()) as FinalAuditResult;
}

export async function polishText(text: string): Promise<PolishResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/analyses/polish`, {
      method: "POST",
      headers: await authHeaders(),
      body: JSON.stringify({ text }),
    });
  } catch {
    throw new AnalysisError(
      `Die ClaimGuard-API unter ${API_BASE} antwortet nicht.`,
      "api_unreachable",
      0,
    );
  }
  if (!response.ok) {
    let code = "polish_failed";
    let message = `Schluss-Korrektur fehlgeschlagen (HTTP ${response.status}).`;
    try {
      const body = await response.json();
      const detail = body?.detail ?? body;
      if (detail?.code) code = detail.code;
      if (detail?.message) message = detail.message;
    } catch {
      // keep defaults
    }
    throw new AnalysisError(message, code, response.status);
  }
  return (await response.json()) as PolishResponse;
}

export async function rewriteAllClaims(
  claims: EvaluatedClaim[],
  inputText: string,
): Promise<Record<string, string>> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/analyses/rewrite-batch`, {
      method: "POST",
      headers: await authHeaders(),
      body: JSON.stringify({ claims, input_text: inputText }),
    });
  } catch {
    throw new AnalysisError(
      `Die ClaimGuard-API unter ${API_BASE} antwortet nicht.`,
      "api_unreachable",
      0,
    );
  }
  if (!response.ok) {
    let code = "rewrite_failed";
    let message = `Reformulierung fehlgeschlagen (HTTP ${response.status}).`;
    try {
      const body = await response.json();
      const detail = body?.detail ?? body;
      if (detail?.code) code = detail.code;
      if (detail?.message) message = detail.message;
    } catch {
      // keep defaults
    }
    throw new AnalysisError(message, code, response.status);
  }
  const data = (await response.json()) as RewriteBatchResponse;
  return data.rewrites ?? {};
}

export async function extractUrl(url: string): Promise<UrlExtractResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/extract/url`, {
      method: "POST",
      headers: await authHeaders(),
      body: JSON.stringify({ url }),
    });
  } catch {
    throw new AnalysisError(
      `Die ClaimGuard-API unter ${API_BASE} antwortet nicht. Läuft der Backend-Server?`,
      "api_unreachable",
      0,
    );
  }

  if (!response.ok) {
    let code = "url_invalid";
    let message = `URL-Extraktion fehlgeschlagen (HTTP ${response.status}).`;
    try {
      const body = await response.json();
      const detail = body?.detail ?? body;
      if (detail?.code) code = detail.code;
      if (detail?.message) message = detail.message;
    } catch {
      // keep defaults
    }
    throw new AnalysisError(message, code, response.status);
  }

  return (await response.json()) as UrlExtractResponse;
}
