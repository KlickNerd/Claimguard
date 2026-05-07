from fastapi import APIRouter, Depends, HTTPException, status

from app.pipelines.claim_detection import DetectionOnlyPipeline, PipelineError
from app.schemas.analysis import AnalysisError, AnalysisRequest, AnalysisResponse
from app.services.anthropic_client import AnthropicServiceError
from app.services.claim_detector import ClaimDetector
from app.services.claim_evaluator import ClaimEvaluator
from app.services.retrieval_service import get_retrieval_service

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


def get_pipeline() -> DetectionOnlyPipeline:
    return DetectionOnlyPipeline(
        detector=ClaimDetector(),
        evaluator=ClaimEvaluator(),
        retriever=get_retrieval_service(),
    )


@router.post(
    "",
    response_model=AnalysisResponse,
    responses={
        400: {"model": AnalysisError},
        422: {"model": AnalysisError},
        503: {"model": AnalysisError},
    },
)
async def create_analysis(
    payload: AnalysisRequest,
    pipeline: DetectionOnlyPipeline = Depends(get_pipeline),
) -> AnalysisResponse:
    try:
        return await pipeline.run(
            input_text=payload.input_text,
            source_type=payload.source_type,
            source_reference=payload.source_reference,
        )
    except PipelineError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except AnthropicServiceError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "anthropic_unavailable", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "schema_violation", "message": str(exc)},
        ) from exc
