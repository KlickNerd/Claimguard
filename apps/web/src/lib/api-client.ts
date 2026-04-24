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

export type AnalysisResponse = {
  id: string;
  status: "completed";
  source_type: "text" | "url" | "pdf";
  source_reference: string | null;
  input_text: string;
  detected_claims: DetectedClaim[];
  prompt_version: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
  created_at: string;
  warnings: string[];
};

export type AnalysisRequest = {
  source_type?: "text" | "url" | "pdf";
  source_reference?: string | null;
  input_text: string;
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

export async function createAnalysis(
  payload: AnalysisRequest,
): Promise<AnalysisResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/analyses`, {
      method: "POST",
      headers: { "content-type": "application/json" },
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
