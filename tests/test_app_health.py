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


def test_local_control_room_reports_real_device_snapshot():
    response = client.get("/api/v2/local/control-room")

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "LOCAL_REALTIME_CONTROL_ROOM"
    assert body["gateway"]["status"] in {"awake", "healthy"}
    assert body["device"]["hostname"]
    assert body["device"]["platform"]
    assert "disk" in body["device"]
    assert body["live_stream_url"] == "/api/v2/local/control-room/stream"


def test_local_proof_endpoint_masks_input_and_returns_real_diagnostics():
    response = client.post(
        "/api/v2/local/proxy/proof",
        json={
            "text": "Customer Aadhaar 2345 6789 0123 and PAN ABCDE1234F must stay local.",
            "actor": "local-health-test",
            "source_app": "pytest",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "LOCAL_REALTIME_PROOF"
    assert body["protected_prompt"] != body["raw_prompt"]
    assert "[Aadhaar_" in body["protected_prompt"]
    assert "device" in body
    assert body["device"]["platform"]


def test_local_evidence_certificate_uses_real_ledger_surface():
    response = client.get("/api/v2/local/evidence-certificate")

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "LOCAL_REALTIME_EVIDENCE"
    assert body["certificate"]
    assert "download_url" in body
