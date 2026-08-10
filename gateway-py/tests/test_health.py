from fastapi.testclient import TestClient

from gateway_py.health.schemas import HealthStatusResponse


def test_health_schema() -> None:
    res = HealthStatusResponse()
    assert res.status == "ok"


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
