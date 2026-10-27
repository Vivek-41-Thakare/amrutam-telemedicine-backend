from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness_is_available_without_database():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_openapi_document_is_available():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "paths" in response.json()


def test_protected_endpoint_requires_authentication():
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_invalid_token_is_rejected():
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert response.status_code == 401


def test_patient_cannot_access_admin_analytics():
    from app.core.security import create_access_token

    token = create_access_token(
        "00000000-0000-0000-0000-000000000000",
        "patient",
    )

    response = client.get(
        "/api/v1/admin/analytics/consultations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401