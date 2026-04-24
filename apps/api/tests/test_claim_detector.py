from typing import Any

import pytest

from app.schemas.claim import DetectionResult
from app.services.claim_detector import ClaimDetector


SAMPLE_INPUT = (
    "Unser Magnesium-Komplex unterstützt eine normale Muskelfunktion und sorgt "
    "für einen energiegeladenen Tag. Stärkt zusätzlich das Immunsystem und beugt "
    "Erkältungen vor."
)


class StubCaller:
    def __init__(self, tool_input: dict[str, Any]) -> None:
        self.tool_input = tool_input
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        *,
        model: str,
        system: str | None,
        user_content: str,
        tool: dict[str, Any],
        max_tokens: int = 4096,
    ) -> tuple[dict[str, Any], int, int]:
        self.calls.append(
            {
                "model": model,
                "user_content": user_content,
                "tool_name": tool["name"],
            },
        )
        return (self.tool_input, 1_234, 567)


@pytest.fixture
def detector_factory():
    def _make(tool_input: dict[str, Any]) -> tuple[ClaimDetector, StubCaller]:
        caller = StubCaller(tool_input)
        detector = ClaimDetector(tool_caller=caller, model="stub-model")
        return detector, caller

    return _make


def test_detect_maps_claims_and_positions(detector_factory) -> None:
    tool_input = {
        "claims": [
            {
                "claim_text": "unterstützt eine normale Muskelfunktion",
                "claim_type": "health_based",
                "nutrient": "Magnesium",
                "implicitness": "explicit",
            },
            {
                "claim_text": "für einen energiegeladenen Tag",
                "claim_type": "wellbeing_based",
                "implicitness": "implicit",
            },
        ],
    }
    detector, caller = detector_factory(tool_input)

    result: DetectionResult = detector.detect(SAMPLE_INPUT)

    assert len(result.claims) == 2
    first, second = result.claims
    assert first.claim_text == "unterstützt eine normale Muskelfunktion"
    assert first.nutrient == "Magnesium"
    # Positions must index into the input verbatim
    assert SAMPLE_INPUT[first.position_start : first.position_end] == first.claim_text
    assert SAMPLE_INPUT[second.position_start : second.position_end] == second.claim_text
    assert result.input_tokens == 1_234
    assert result.output_tokens == 567
    assert caller.calls[0]["model"] == "stub-model"
    assert caller.calls[0]["tool_name"] == "record_detected_claims"


def test_detect_drops_hallucinated_claims_not_in_input(detector_factory) -> None:
    tool_input = {
        "claims": [
            {
                "claim_text": "unterstützt eine normale Muskelfunktion",
                "claim_type": "health_based",
                "implicitness": "explicit",
            },
            # This one doesn't appear verbatim in the input - must be dropped
            {
                "claim_text": "hilft bei Krebs",
                "claim_type": "disease_based",
                "implicitness": "explicit",
            },
        ],
    }
    detector, _ = detector_factory(tool_input)

    result = detector.detect(SAMPLE_INPUT)

    assert len(result.claims) == 1
    assert result.claims[0].claim_text == "unterstützt eine normale Muskelfunktion"


def test_detect_ignores_empty_and_missing_text(detector_factory) -> None:
    tool_input = {
        "claims": [
            {"claim_text": "", "claim_type": "health_based", "implicitness": "explicit"},
            {
                "claim_text": "   ",
                "claim_type": "health_based",
                "implicitness": "explicit",
            },
        ],
    }
    detector, _ = detector_factory(tool_input)

    result = detector.detect(SAMPLE_INPUT)

    assert result.claims == []


def test_detect_treats_empty_string_fields_as_null(detector_factory) -> None:
    tool_input = {
        "claims": [
            {
                "claim_text": "unterstützt eine normale Muskelfunktion",
                "claim_type": "health_based",
                "nutrient": "",  # Claude sometimes passes empty strings
                "substance": "   ",
                "implicitness": "explicit",
            },
        ],
    }
    detector, _ = detector_factory(tool_input)

    result = detector.detect(SAMPLE_INPUT)

    assert result.claims[0].nutrient is None
    assert result.claims[0].substance is None


def test_empty_claims_list_is_valid(detector_factory) -> None:
    detector, _ = detector_factory({"claims": []})

    result = detector.detect(SAMPLE_INPUT)

    assert result.claims == []
    assert result.input_tokens == 1_234
