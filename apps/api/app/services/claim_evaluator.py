from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Literal, Protocol

from app.config import settings
from app.schemas.claim import (
    DetectedClaim,
    EvaluatedClaim,
    EvaluationResult,
    LegalHint,
)
from app.schemas.retrieval import RetrievalHit
from app.services.anthropic_client import AnthropicServiceError, create_message_with_tool
from app.services.prompt_loader import PromptLoader, get_prompt_loader

logger = logging.getLogger(__name__)


EvaluatorMode = Literal["quick", "full"]


EVALUATION_TOOL: dict[str, Any] = {
    "name": "record_claim_evaluation",
    "description": (
        "Record the legal verdict for a single health claim. Use confidence "
        "below 0.6 to signal that the verdict is uncertain."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["allowed", "borderline", "forbidden", "unclear"],
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "risk_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
            },
            "reasoning": {
                "type": "string",
                "description": "2-4 sentence German explanation, accessible to non-lawyers.",
            },
            "rewrite_suggestion": {
                "type": "string",
                "description": (
                    "Alternative German formulation that preserves the marketing "
                    "intent without the legal risk. Null for allowed claims."
                ),
            },
            "legal_hints": {
                "type": "array",
                "description": (
                    "0-3 references the verdict relies on. In full mode, every "
                    "entry MUST cite a chunk_id from the supplied evidence list."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "reference": {"type": "string"},
                        "rationale": {"type": "string"},
                        "chunk_id": {
                            "type": "string",
                            "description": (
                                "ID of the source chunk in the curated KB. Required "
                                "in full mode, optional in quick mode."
                            ),
                        },
                    },
                    "required": ["reference", "rationale"],
                },
            },
        },
        "required": [
            "status",
            "confidence",
            "risk_level",
            "reasoning",
            "legal_hints",
        ],
    },
}

_CONTEXT_WINDOW_CHARS = 100


class _ToolCaller(Protocol):
    def __call__(
        self,
        *,
        model: str,
        system: str | None,
        user_content: str,
        tool: dict[str, Any],
        max_tokens: int = ...,
        cache_system: bool = ...,
    ) -> tuple[dict[str, Any], int, int]: ...


class ClaimEvaluator:
    """Per-claim LLM evaluation, two modes:

    - ``quick``: Sonnet, no retrieval — bridges the gap before PROJ-9 lands.
    - ``full``: Opus + system-prompt + retrieval evidence (PROJ-10 design).

    The constructor picks the default mode. ``full`` mode falls back to
    Sonnet+full if Opus fails three times, so the user still gets a verdict
    (with a degraded-mode warning) when Anthropic has issues.
    """

    def __init__(
        self,
        *,
        prompt_loader: PromptLoader | None = None,
        tool_caller: _ToolCaller | None = None,
        mode: EvaluatorMode = "full",
        full_model: str | None = None,
        quick_model: str | None = None,
        max_concurrency: int = 5,
    ) -> None:
        self._loader = prompt_loader or get_prompt_loader()
        self._call = tool_caller or create_message_with_tool
        self._mode = mode
        self._full_model = full_model or settings.anthropic_model_evaluation
        self._quick_model = quick_model or settings.anthropic_model_detection
        self._max_concurrency = max_concurrency

    async def evaluate_all(
        self,
        *,
        claims: list[DetectedClaim],
        full_text: str,
        evidence_per_claim: dict[str, list[RetrievalHit]] | None = None,
    ) -> EvaluationResult:
        if not claims:
            return EvaluationResult(
                evaluated_claims=[],
                total_input_tokens=0,
                total_output_tokens=0,
                latency_ms=0,
            )

        evidence_per_claim = evidence_per_claim or {}
        started = time.perf_counter()
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def bounded(claim: DetectedClaim) -> tuple[EvaluatedClaim | None, int, int]:
            async with semaphore:
                evidence = evidence_per_claim.get(str(claim.id), [])
                return await asyncio.to_thread(
                    self._evaluate_single,
                    claim,
                    full_text,
                    evidence,
                )

        results = await asyncio.gather(*(bounded(c) for c in claims))

        evaluated: list[EvaluatedClaim] = []
        total_in = 0
        total_out = 0
        for ec, in_tok, out_tok in results:
            total_in += in_tok
            total_out += out_tok
            if ec is not None:
                evaluated.append(ec)

        evaluated.sort(key=lambda c: c.position_start)

        return EvaluationResult(
            evaluated_claims=evaluated,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    def _evaluate_single(
        self,
        claim: DetectedClaim,
        full_text: str,
        evidence: list[RetrievalHit],
    ) -> tuple[EvaluatedClaim | None, int, int]:
        # Hard rule before spending an LLM call: disease-based claims are
        # never legal for foods (Art. 7 LMIV, § 12 LFGB). Saves cost + avoids
        # rare LLM mis-classifications on the highest-risk category.
        if claim.claim_type == "disease_based":
            return self._disease_shortcut(claim, evidence), 0, 0

        if self._mode == "full":
            return self._evaluate_full(claim, full_text, evidence)
        return self._evaluate_quick(claim, full_text)

    def _evaluate_full(
        self,
        claim: DetectedClaim,
        full_text: str,
        evidence: list[RetrievalHit],
    ) -> tuple[EvaluatedClaim | None, int, int]:
        system_template = self._loader.get("claim_evaluation_system")
        user_template = self._loader.get("claim_evaluation")
        context = self._surrounding_context(full_text, claim)

        rendered = self._loader.render(
            "claim_evaluation",
            {
                "claim": {
                    "claim_text": claim.claim_text,
                    "claim_type": claim.claim_type,
                    "nutrient": claim.nutrient,
                    "substance": claim.substance,
                    "implicitness": claim.implicitness,
                },
                "context": context,
                "evidence": [hit.model_dump() for hit in evidence],
            },
            version=user_template.metadata.version,
        )

        try:
            tool_input, in_tok, out_tok = self._call(
                model=self._full_model,
                system=system_template.body,
                user_content=rendered.rendered,
                tool=EVALUATION_TOOL,
                cache_system=True,
            )
            model_used = self._full_model
            prompt_version = user_template.metadata.version
        except AnthropicServiceError as exc:
            logger.warning(
                "Opus evaluation failed for %s, falling back to %s: %s",
                claim.id,
                self._quick_model,
                exc,
            )
            try:
                tool_input, in_tok, out_tok = self._call(
                    model=self._quick_model,
                    system=system_template.body,
                    user_content=rendered.rendered,
                    tool=EVALUATION_TOOL,
                    cache_system=True,
                )
                model_used = self._quick_model
                prompt_version = f"{user_template.metadata.version}+sonnet-fallback"
            except Exception as inner:
                logger.warning("Sonnet fallback also failed for %s: %s", claim.id, inner)
                return None, 0, 0
        except Exception as exc:
            logger.warning("Evaluation failed for claim %s: %s", claim.id, exc)
            return None, 0, 0

        return self._build_evaluated(
            claim,
            tool_input,
            evidence=evidence,
            model_used=model_used,
            prompt_version=prompt_version,
            in_tokens=in_tok,
            out_tokens=out_tok,
        )

    def _evaluate_quick(
        self,
        claim: DetectedClaim,
        full_text: str,
    ) -> tuple[EvaluatedClaim | None, int, int]:
        template = self._loader.get("claim_evaluation_quick")
        context = self._surrounding_context(full_text, claim)
        try:
            rendered = self._loader.render(
                "claim_evaluation_quick",
                {
                    "claim": {
                        "claim_text": claim.claim_text,
                        "claim_type": claim.claim_type,
                        "nutrient": claim.nutrient,
                        "substance": claim.substance,
                        "implicitness": claim.implicitness,
                    },
                    "context": context,
                },
                version=template.metadata.version,
            )
            tool_input, in_tok, out_tok = self._call(
                model=self._quick_model,
                system=None,
                user_content=rendered.rendered,
                tool=EVALUATION_TOOL,
            )
        except Exception as exc:
            logger.warning("Quick evaluation failed for claim %s: %s", claim.id, exc)
            return None, 0, 0

        return self._build_evaluated(
            claim,
            tool_input,
            evidence=[],
            model_used=self._quick_model,
            prompt_version=template.metadata.version,
            in_tokens=in_tok,
            out_tokens=out_tok,
        )

    def _build_evaluated(
        self,
        claim: DetectedClaim,
        tool_input: dict[str, Any],
        *,
        evidence: list[RetrievalHit],
        model_used: str,
        prompt_version: str,
        in_tokens: int,
        out_tokens: int,
    ) -> tuple[EvaluatedClaim | None, int, int]:
        # Robust against LLM schema-fuzzing: every field gets coerced to a
        # sane default if the model returns something we can't validate. We
        # log the offending tool_input once so we can spot patterns, but
        # the user gets a usable verdict instead of "Schema-Fehler" in the
        # report.
        status = _coerce_status(tool_input.get("status"))
        risk_level = _coerce_risk(tool_input.get("risk_level"))
        confidence = _coerce_confidence(tool_input.get("confidence"))
        reasoning = _coerce_reasoning(tool_input.get("reasoning"))
        rewrite = _nullable(tool_input.get("rewrite_suggestion"))

        coerced_keys = []
        if status != tool_input.get("status"):
            coerced_keys.append(f"status={tool_input.get('status')!r}")
        if risk_level != tool_input.get("risk_level"):
            coerced_keys.append(f"risk_level={tool_input.get('risk_level')!r}")
        if coerced_keys:
            logger.warning(
                "Coerced LLM output for %s (%s); raw tool_input keys=%s",
                claim.id,
                ", ".join(coerced_keys),
                sorted(tool_input.keys()),
            )

        try:
            evaluated = EvaluatedClaim(
                **claim.model_dump(),
                status=status,
                confidence=confidence,
                risk_level=risk_level,
                reasoning=reasoning,
                rewrite_suggestion=rewrite,
                legal_hints=_build_hints(tool_input.get("legal_hints", []), evidence),
                evidence=evidence,
                evaluation_model=model_used,
                evaluation_prompt_version=prompt_version,
            )
        except (KeyError, ValueError, TypeError) as exc:
            # Should be unreachable now that everything is coerced - log
            # the offending payload (snippet, not full snapshot, to keep
            # logs readable) and bail with None so the UI surfaces it.
            logger.warning(
                "Schema violation in evaluation for %s: %s; raw=%s",
                claim.id,
                exc,
                {k: str(v)[:120] for k, v in tool_input.items()},
            )
            return None, in_tokens, out_tokens

        if evaluated.confidence < 0.6 and evaluated.status != "unclear":
            evaluated = evaluated.model_copy(
                update={"status": "unclear", "rewrite_suggestion": None},
            )

        return evaluated, in_tokens, out_tokens

    def _disease_shortcut(
        self,
        claim: DetectedClaim,
        evidence: list[RetrievalHit],
    ) -> EvaluatedClaim:
        """Bypass the LLM for disease-based claims - they are categorically
        forbidden for foods under Art. 7 LMIV / § 12 LFGB."""
        return EvaluatedClaim(
            **claim.model_dump(),
            status="forbidden",
            confidence=0.98,
            risk_level="high",
            reasoning=(
                "Krankheitsbezogene Aussagen sind für Lebensmittel grundsätzlich "
                "unzulässig (Art. 7 Abs. 3 LMIV, § 12 Abs. 1 Nr. 1 LFGB). Die "
                "Vorbeugung, Linderung oder Heilung von Krankheiten darf nur "
                "Arzneimitteln zugeschrieben werden."
            ),
            rewrite_suggestion=None,
            legal_hints=[
                LegalHint(
                    reference="Art. 7 Abs. 3 LMIV (VO 1169/2011)",
                    rationale="Verbietet krankheitsbezogene Aussagen für Lebensmittel.",
                    verified=False,
                ),
                LegalHint(
                    reference="§ 12 Abs. 1 Nr. 1 LFGB",
                    rationale="Nationales Verbot krankheitsbezogener Lebensmittelwerbung.",
                    verified=False,
                ),
            ],
            evidence=evidence,
            evaluation_model="rule:disease_shortcut",
            evaluation_prompt_version="1.0.0",
        )

    def _surrounding_context(self, full_text: str, claim: DetectedClaim) -> str:
        start = max(0, claim.position_start - _CONTEXT_WINDOW_CHARS)
        end = min(len(full_text), claim.position_end + _CONTEXT_WINDOW_CHARS)
        snippet = full_text[start:end]
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(full_text) else ""
        return f"{prefix}{snippet}{suffix}"


def _build_hints(
    raw_hints: list[dict[str, Any]],
    evidence: list[RetrievalHit],
) -> list[LegalHint]:
    """Coerce LLM hints into ``LegalHint`` and verify any chunk_ids.

    A chunk_id is considered verified when the chunk exists in the supplied
    evidence pool - this is the hallucination check from PROJ-10's design:
    the model isn't allowed to cite sources we didn't show it.
    """
    by_id = {hit.chunk_id: hit for hit in evidence}
    hints: list[LegalHint] = []
    for raw in raw_hints:
        try:
            reference = str(raw["reference"])
            rationale = str(raw["rationale"])
        except (KeyError, TypeError):
            continue
        chunk_id = raw.get("chunk_id")
        verified = False
        url: str | None = None
        if chunk_id and chunk_id in by_id:
            verified = True
            url = by_id[chunk_id].url or None
        else:
            chunk_id = None
        hints.append(
            LegalHint(
                reference=reference,
                rationale=rationale,
                verified=verified,
                chunk_id=chunk_id,
                url=url,
            ),
        )
    return hints


def _nullable(value: Any) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


_VALID_STATUS = {"allowed", "borderline", "forbidden", "unclear"}
_VALID_RISK = {"low", "medium", "high"}

_DEFAULT_REASONING = (
    "Die Bewertung konnte nicht vollständig validiert werden - "
    "bitte den Claim manuell prüfen."
)

# Loose synonyms the LLM occasionally drifts into. Mapping to the
# canonical enum gives a usable verdict instead of dropping the claim.
_STATUS_SYNONYMS = {
    "permitted": "allowed",
    "compliant": "allowed",
    "ok": "allowed",
    "zulässig": "allowed",
    "zulaessig": "allowed",
    "questionable": "borderline",
    "grenzwertig": "borderline",
    "risiko": "borderline",
    "risk": "borderline",
    "prohibited": "forbidden",
    "verboten": "forbidden",
    "unzulässig": "forbidden",
    "unzulaessig": "forbidden",
    "uncertain": "unclear",
    "unknown": "unclear",
    "unsicher": "unclear",
    "unklar": "unclear",
}

_RISK_SYNONYMS = {
    "niedrig": "low",
    "gering": "low",
    "mittel": "medium",
    "moderate": "medium",
    "hoch": "high",
}


def _coerce_status(value: Any) -> str:
    if isinstance(value, str):
        norm = value.strip().lower()
        if norm in _VALID_STATUS:
            return norm
        if norm in _STATUS_SYNONYMS:
            return _STATUS_SYNONYMS[norm]
    return "unclear"


def _coerce_risk(value: Any) -> str:
    if isinstance(value, str):
        norm = value.strip().lower()
        if norm in _VALID_RISK:
            return norm
        if norm in _RISK_SYNONYMS:
            return _RISK_SYNONYMS[norm]
    return "medium"


def _coerce_confidence(value: Any) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, f))


def _coerce_reasoning(value: Any) -> str:
    if value is None:
        return _DEFAULT_REASONING
    text = str(value).strip()
    return text or (
        "Die Bewertung konnte nicht vollständig validiert werden - bitte den Claim manuell prüfen."
    )
