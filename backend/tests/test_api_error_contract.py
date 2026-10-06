from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_not_found_errors_include_a_request_id() -> None:
    response = client.get("/api/v1/not-a-real-route", headers={"X-Request-ID": "req-test-404"})

    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "req-test-404"
    assert response.json() == {
        "detail": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "Not Found",
            "request_id": "req-test-404",
        }
    }


def test_validation_errors_include_safe_machine_and_human_details() -> None:
    response = client.post("/api/v1/auth/register", json={})

    assert response.status_code == 422
    error = response.json()["detail"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"] == "One or more fields are invalid."
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert error["details"]
