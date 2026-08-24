from fastapi.testclient import TestClient

from gateway_py.health.schemas import HealthStatusResponse, ReadinessStatusResponse


def test_health_schema() -> None:
    res = HealthStatusResponse()
    assert res.status == "ok"


def test_readiness_schema() -> None:
    res = ReadinessStatusResponse()
    assert res.status == "ok"


def test_livez_endpoint(client: TestClient) -> None:
    response = client.get("/livez")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_endpoint(client: TestClient) -> None:
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_not_found(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 404
