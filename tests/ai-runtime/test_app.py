from fastapi.testclient import TestClient

from app import app


def test_health_returns_success() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_investigation_returns_safe_service_error_without_runtime_configuration() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/internal/investigations",
            json={
                "investigationId": "inv-002-001",
                "question": "What happened?",
                "service": "checkout-api",
            },
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Investigation service unavailable."}


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