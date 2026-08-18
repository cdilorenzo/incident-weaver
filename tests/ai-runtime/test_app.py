import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import app


def test_health_returns_success() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_investigation_contract_fixture_returns_deterministic_result() -> None:
    contracts = Path(__file__).parents[2] / "contracts"
    request = json.loads((contracts / "investigation-request.json").read_text())
    expected = json.loads((contracts / "investigation-result.json").read_text())

    with TestClient(app) as client:
        response = client.post("/internal/investigations", json=request)

    assert response.status_code == 200
    assert response.json() == expected


def test_investigation_rejects_unknown_fields() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/internal/investigations",
            json={
                "investigationId": "inv-002-001",
                "question": "What happened?",
                "service": "checkout-api",
                "unexpected": "not part of the contract",
            },
        )

    assert response.status_code == 422