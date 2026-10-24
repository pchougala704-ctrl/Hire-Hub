from app import create_app


def test_auth_pages_render_csrf_token():
    app = create_app({
        "SECRET_KEY": "test-only-secret",
        "TESTING": True,
        "MONGO_URI": "mongodb://localhost:27017",
        "MONGO_DATABASE": "hirehub_test",
    })
    client = app.test_client()
    for path in ("/login", "/register"):
        response = client.get(path)
        assert response.status_code == 200
        assert b"csrf_token" in response.data
    assert client.get("/api/auth/csrf").status_code == 200


def test_state_changing_api_request_requires_csrf():
    app = create_app({
        "SECRET_KEY": "test-only-secret",
        "TESTING": True,
        "MONGO_URI": "mongodb://localhost:27017",
        "MONGO_DATABASE": "hirehub_test",
    })
    response = app.test_client().post("/api/auth/login", json={})
    assert response.status_code == 400
    assert response.json["error_code"] == "CSRF_FAILED"


def test_api_reports_unauthenticated_access_with_401():
    app = create_app({"SECRET_KEY": "test-only-secret", "TESTING": True})
    response = app.test_client().get("/api/auth/me")
    assert response.status_code == 401
    assert response.json["error_code"] == "AUTHENTICATION_REQUIRED"
