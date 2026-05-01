import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app import app, get_active_user  # noqa: E402
from auth.jwt_handler import TokenPayload  # noqa: E402
from integrations.webhook_engine import WebhookDispatcher, WebhookPayload, OutboundWebhook  # noqa: E402


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


def test_deployment_doctor_license_usage_and_model_benchmark(monkeypatch):
    c = client()
    doctor = c.get("/api/v2/enterprise/deployment-doctor")
    assert doctor.status_code == 200
    assert "checks" in doctor.json()

    usage = c.get("/api/v2/enterprise/license-usage")
    assert usage.status_code == 200
    assert "active_users" in usage.json()

    monkeypatch.setattr("app.model_router.route", lambda prompt, sensitivity_score=8.0: {
        "answer": "Protected [Aadhaar_1] response",
        "model_used": "ollama/test",
        "fallback_used": False,
    })
    bench = c.post("/api/v2/enterprise/model-benchmark")
    assert bench.status_code == 200
    assert len(bench.json()["results"]) == 3


def test_break_glass_tenant_export_import_and_policy_versions():
    c = client()
    bg = c.post("/api/v2/enterprise/break-glass", json={
        "reason": "Emergency buyer recovery drill",
        "duration_minutes": 15,
    })
    assert bg.status_code == 200
    assert bg.json()["break_glass_token"]

    exported = c.get("/api/v2/enterprise/tenant/export")
    assert exported.status_code == 200
    assert exported.json()["certificate"]

    imported = c.post("/api/v2/enterprise/tenant/import", json={
        "bundle": exported.json(),
        "dry_run": True,
    })
    assert imported.status_code == 200
    assert imported.json()["status"] == "DRY_RUN_OK"

    version = c.post("/api/v2/enterprise/policy-versions", json={
        "bundle_name": "buyer-policy-v1",
        "yaml_content": "rules: []",
        "approval_state": "approved",
    })
    assert version.status_code == 200
    assert version.json()["version"]["certificate"]

    versions = c.get("/api/v2/enterprise/policy-versions")
    assert versions.status_code == 200
    assert versions.json()["versions"]


def test_webhook_dispatcher_queues_failed_delivery(tmp_path):
    dispatcher = WebhookDispatcher()
    dispatcher._registry = []
    dispatcher._registry_path = lambda: str(tmp_path / "registry.json")
    dispatcher._queue_path = lambda: str(tmp_path / "queue.jsonl")
    hook_id = dispatcher.register(OutboundWebhook(
        target_url="http://127.0.0.1:9/nowhere",
        event_types=["CISO_ALERT"],
        tenant_id="default",
    ))
    assert hook_id
    dispatcher.dispatch(WebhookPayload(event_type="CISO_ALERT", payload={"x": 1}))
    queued = dispatcher.queued_deliveries()
    assert len(queued) == 1
