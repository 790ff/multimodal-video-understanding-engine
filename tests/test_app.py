from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_videos_router_is_registered() -> None:
    with TestClient(app) as client:
        response = client.get("/videos")

    assert response.status_code == 200
    assert response.json() == {
        "module": "videos",
        "status": "ready",
        "milestone": "M1 scaffold",
    }
