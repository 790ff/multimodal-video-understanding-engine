from fastapi.testclient import TestClient

from app.config import get_settings
from app.domain.errors import AppError
from app.main import app, create_app


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_schema_loads() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Multimodal Video Understanding Engine"


def test_frontend_cors_preflight_allows_local_vite_origin(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    )
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.options(
            "/videos/upload",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "POST",
            },
        )

    get_settings.cache_clear()
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_frontend_cors_preflight_rejects_unconfigured_origin(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    )
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        response = client.options(
            "/videos/upload",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "POST",
            },
        )

    get_settings.cache_clear()
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_allowed_origins_are_environment_driven(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://product.local:5173")
    get_settings.cache_clear()

    with TestClient(create_app()) as client:
        allowed_response = client.options(
            "/videos/upload",
            headers={
                "Origin": "http://product.local:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        default_response = client.options(
            "/videos/upload",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "POST",
            },
        )

    get_settings.cache_clear()
    assert allowed_response.status_code == 200
    assert allowed_response.headers["access-control-allow-origin"] == "http://product.local:5173"
    assert default_response.status_code == 400
    assert "access-control-allow-origin" not in default_response.headers


def test_app_error_response_sanitizes_sensitive_details(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://127.0.0.1:5173")
    get_settings.cache_clear()
    application = create_app()

    @application.get("/secret-error")
    def secret_error() -> None:
        raise AppError(
            "OPENAI_API_KEY=abc123 failed while reading /Users/thamer/project/.env",
            details={
                "safe": "kept",
                "path": "/Users/thamer/project/.env",
                "OPENAI_API_KEY": "abc123",
            },
        )

    with TestClient(application) as client:
        response = client.get("/secret-error")

    get_settings.cache_clear()
    assert response.status_code == 500
    assert "OPENAI_API_KEY" not in response.text
    assert "/Users/thamer/project/.env" not in response.text
    assert response.json() == {
        "error": {
            "code": "application_error",
            "message": "An application error occurred.",
            "details": {"safe": "kept", "path": "[redacted]"},
        }
    }


def test_media_runtime_folders_are_not_public_static_routes() -> None:
    with TestClient(app) as client:
        responses = [
            client.get("/uploads/video-id/original.mp4"),
            client.get("/audio/video-id/audio.wav"),
            client.get("/frames/video-id/frame_000001.jpg"),
            client.get("/data/uploads/video-id/original.mp4"),
            client.get("/data/audio/video-id/audio.wav"),
            client.get("/data/frames/video-id/frame_000001.jpg"),
        ]

    assert [response.status_code for response in responses] == [404, 404, 404, 404, 404, 404]
