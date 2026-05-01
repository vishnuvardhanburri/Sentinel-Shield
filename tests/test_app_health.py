import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app import app


client = TestClient(app)


def test_health_endpoint_has_security_headers():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] in {"awake", "healthy"}
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_root_endpoint_is_xavira_branded():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["signature"] == "BY XAVIRA TECH LABS"


def test_suspicious_env_probe_is_blocked():
    response = client.get("/.env")

    assert response.status_code == 404
    assert response.json()["detail"] == "NOT_FOUND"
