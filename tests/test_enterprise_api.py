import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app import app, get_active_user
from auth.jwt_handler import TokenPayload


def super_admin():
    return TokenPayload(
        sub="admin@sentinel.local",
        email="admin@sentinel.local",
        role="SUPER_ADMIN",
        department="GLOBAL_SECURITY",
        tenant_id="default",
    )


def client():
    app.dependency_overrides[get_active_user] = super_admin
    return TestClient(app)


def test_enterprise_model_center_and_version():
    c = client()
    assert c.get("/api/v2/enterprise/models").status_code == 200
    version = c.get("/api/v2/enterprise/version")
    assert version.status_code == 200
    assert version.json()["product"] == "Sovereign Shield"


def test_model_pull_is_disabled_by_default():
    response = client().post("/api/v2/enterprise/models/pull", json={"model": "llama3.1"})

    assert response.status_code == 403
    assert response.json()["detail"] == "MODEL_PULL_DISABLED"


def test_enterprise_firewall_bundle_mtls_branding_and_anchor():
    c = client()
    firewall = c.post("/api/v2/enterprise/firewall/rules", json={
        "name": "Block Test",
        "action": "quarantine",
        "pattern": "secret merger",
        "severity": 9,
    })
    assert firewall.status_code == 200
    assert "LLM Firewall" in firewall.json()["yaml"]

    bundle = c.post("/api/v2/enterprise/policy-bundles/sign", json={
        "bundle_name": "test-bundle",
        "yaml_content": firewall.json()["yaml"],
        "target_scope": "edge",
    })
    assert bundle.status_code == 200
    assert len(bundle.json()["signature"]) == 64

    mtls = c.post("/api/v2/enterprise/mtls/nginx", json={"server_name": "sentinel.local"})
    assert mtls.status_code == 200
    assert "ssl_verify_client on" in mtls.json()["nginx_config"]

    branding = c.post("/api/v2/enterprise/branding", json={"company_name": "Buyer Co"})
    assert branding.status_code == 200
    assert branding.json()["branding"]["company_name"] == "Buyer Co"

    anchor = c.post("/api/v2/enterprise/ledger/anchor")
    assert anchor.status_code == 200
    assert len(anchor.json()["anchor"]["ledger_root"]) == 64


def test_enterprise_reports_alerts_and_quarantine_lists():
    c = client()
    assert c.get("/api/v2/enterprise/reports").status_code == 200
    assert c.get("/api/v2/enterprise/alerts").status_code == 200
    assert c.get("/api/v2/enterprise/quarantine").status_code == 200


def test_enterprise_control_room_snapshot_and_stream():
    c = client()
    snapshot = c.get("/api/v2/enterprise/control-room")
    assert snapshot.status_code == 200
    body = snapshot.json()
    assert body["gateway"]["status"] == "awake"
    assert "readiness" in body
    assert "risk" in body
    assert "recent_events" in body
    assert body["live_stream_url"] == "/api/v2/enterprise/control-room/stream"

    with c.stream("GET", "/api/v2/enterprise/control-room/stream?max_events=1&interval_seconds=0.5") as response:
        payload = response.read().decode()
    assert "event: control-room" in payload
    assert "\"gateway\"" in payload


def test_enterprise_readiness_backup_restore_and_threat_model():
    c = client()
    readiness = c.get("/api/v2/enterprise/readiness")
    assert readiness.status_code == 200
    assert "score" in readiness.json()
    assert any(control["name"] == "ledger_integrity" for control in readiness.json()["controls"])

    backup = c.post("/api/v2/enterprise/backup")
    assert backup.status_code == 200
    assert backup.json()["sha256"]
    assert backup.json()["artifact_count"] >= 1

    restore = c.get("/api/v2/enterprise/restore-drill")
    assert restore.status_code == 200
    assert restore.json()["backup_valid"] is True

    threat_model = c.post("/api/v2/enterprise/threat-model", json={
        "deployment_name": "Buyer Production",
        "internet_exposed": True,
        "cloud_llm_enabled": False,
        "mTLS_enforced": True,
    })
    assert threat_model.status_code == 200
    assert len(threat_model.json()["risk_register"]) >= 5
    assert threat_model.json()["certificate"]


def test_policy_bundle_verify_detects_signature_tamper():
    c = client()
    bundle = c.post("/api/v2/enterprise/policy-bundles/sign", json={
        "bundle_name": "verify-bundle",
        "yaml_content": "rules: []",
        "target_scope": "edge",
    }).json()

    ok = c.post("/api/v2/enterprise/policy-bundles/verify", json={
        "manifest": bundle["manifest"],
        "signature": bundle["signature"],
    })
    assert ok.status_code == 200
    assert ok.json()["valid"] is True

    tampered = dict(bundle["manifest"])
    tampered["target_scope"] = "attacker-edge"
    bad = c.post("/api/v2/enterprise/policy-bundles/verify", json={
        "manifest": tampered,
        "signature": bundle["signature"],
    })
    assert bad.status_code == 200
    assert bad.json()["valid"] is False
