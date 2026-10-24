from app import create_app


def test_api_rejects_non_object_json_payload():
    app = create_app({"SECRET_KEY": "test-only-secret", "TESTING": True})
    client = app.test_client()
    token = client.get("/api/auth/csrf").json["data"]["csrf_token"]
    response = client.post(
        "/api/auth/login",
        json=["not", "an", "object"],
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 400
    assert response.json["error_code"] == "VALIDATION_ERROR"
