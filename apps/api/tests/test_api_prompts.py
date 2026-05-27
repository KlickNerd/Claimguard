from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "development"}


def test_list_prompts_contains_bundled_tasks() -> None:
    response = client.get("/api/prompts")
    assert response.status_code == 200

    tasks = response.json()["tasks"]
    assert "claim_detection" in tasks
    assert "claim_evaluation" in tasks
    # All historic versions stay available - the loader returns them
    # newest-first. We just assert that the 1.x history is intact.
    assert "1.0.0" in tasks["claim_detection"]
    assert "1.1.0" in tasks["claim_detection"]


def test_get_metadata_returns_latest_by_default() -> None:
    response = client.get("/api/prompts/claim_detection/metadata")
    assert response.status_code == 200

    data = response.json()
    # Newest version wins by default. Bumped from 1.0.0 -> 1.1.0 when
    # HWG vocabulary was added (PROJ-19 follow-up, 2026-05-27).
    assert data["version"] == "1.1.0"
    assert data["model"] == "claude-sonnet-4-6"
    assert data["task"] == "claim_detection"


def test_get_metadata_for_unknown_task_is_404() -> None:
    response = client.get("/api/prompts/does_not_exist/metadata")
    assert response.status_code == 404


def test_render_substitutes_variables() -> None:
    response = client.post(
        "/api/prompts/claim_detection/render",
        json={"variables": {"input_text": "Magnesium für jeden Tag."}},
    )
    assert response.status_code == 200

    data = response.json()
    assert "Magnesium für jeden Tag." in data["rendered"]
    assert data["metadata"]["task"] == "claim_detection"


def test_render_missing_variable_is_400() -> None:
    response = client.post(
        "/api/prompts/claim_detection/render",
        json={"variables": {}},
    )
    assert response.status_code == 400
