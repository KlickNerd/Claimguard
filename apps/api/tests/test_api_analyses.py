from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.analyses import get_pipeline
from app.main import app
from app.pipelines.claim_detection import DetectionOnlyPipeline
from app.services.claim_detector import ClaimDetector

client = TestClient(app)


class StubCaller:
    def __init__(self, tool_input: dict[str, Any]) -> None:
        self.tool_input = tool_input

    def __call__(self, **kwargs: Any) -> tuple[dict[str, Any], int, int]:
        return (self.tool_input, 100, 50)


def build_pipeline(tool_input: dict[str, Any]) -> DetectionOnlyPipeline:
    detector = ClaimDetector(
        tool_caller=StubCaller(tool_input),
        model="stub-model",
    )
    return DetectionOnlyPipeline(detector=detector)


DE_INPUT = (
    "Unser Magnesium-Komplex unterstützt eine normale Muskelfunktion und sorgt "
    "für einen energiegeladenen Tag. Stärkt zusätzlich das Immunsystem und beugt "
    "Erkältungen vor."
)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_pipeline, None)


def test_analysis_returns_detected_claims() -> None:
    tool_input = {
        "claims": [
            {
                "claim_text": "unterstützt eine normale Muskelfunktion",
                "claim_type": "health_based",
                "nutrient": "Magnesium",
                "implicitness": "explicit",
            },
        ],
    }
    app.dependency_overrides[get_pipeline] = lambda: build_pipeline(tool_input)

    response = client.post(
        "/api/analyses",
        json={"source_type": "text", "input_text": DE_INPUT},
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "completed"
    assert len(data["detected_claims"]) == 1
    assert data["detected_claims"][0]["nutrient"] == "Magnesium"
    assert data["model"] == "stub-model"


def test_short_input_rejected_with_friendly_400() -> None:
    response = client.post(
        "/api/analyses",
        json={"source_type": "text", "input_text": "Zu kurz."},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "input_too_short"
    assert "50 Zeichen" in detail["message"]


def test_too_long_input_rejected_with_friendly_400() -> None:
    response = client.post(
        "/api/analyses",
        json={"source_type": "text", "input_text": "A" * 50_001},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "input_too_long"
    assert "50.000" in detail["message"]


def test_english_input_rejected() -> None:
    app.dependency_overrides[get_pipeline] = lambda: build_pipeline({"claims": []})

    long_en = (
        "Our magnesium supplement supports healthy muscle function every day. "
        "It helps with energy levels and maintains a good immune response."
    )
    response = client.post(
        "/api/analyses",
        json={"source_type": "text", "input_text": long_en},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "language_not_supported"


def test_no_claims_found_returns_warning() -> None:
    app.dependency_overrides[get_pipeline] = lambda: build_pipeline({"claims": []})

    neutral = (
        "Unser Online-Shop verschickt Bestellungen werktags binnen 24 Stunden. "
        "Versandkosten entfallen ab einem Bestellwert von 50 Euro."
    )
    response = client.post(
        "/api/analyses",
        json={"source_type": "text", "input_text": neutral},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["detected_claims"] == []
    assert any("Keine gesundheitsbezogenen" in w for w in data["warnings"])
