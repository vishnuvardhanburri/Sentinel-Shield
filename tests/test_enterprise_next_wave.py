import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app import app, get_active_user, _totp_code  # noqa: E402
from auth.jwt_handler import TokenPayload  # noqa: E402
from db.models import User  # noqa: E402
from db.session import SessionLocal, init_db  # noqa: E402


def super_admin():
    return TokenPayload(
        sub="admin@sentinel.local",
        email="admin@sentinel.local",
        role="SUPER_ADMIN",
        department="GLOBAL_SECURITY",
        tenant_id="default",
    )


def client():
    init_db()
    app.dependency_overrides[get_active_user] = super_admin
    return TestClient(app)


def test_api_key_lifecycle():
    c = client()
    created = c.post("/api/v2/admin/api-keys", json={
        "name": "CRM Gateway",
        "scopes": ["proxy:inspect"],
        "department": "SALES",
        "expires_in_days": 30,
    })
    assert created.status_code == 200
    body = created.json()
    assert body["secret"].startswith("sshield_")
    key_id = body["api_key"]["id"]

    listed = c.get("/api/v2/admin/api-keys")
    assert listed.status_code == 200
    assert any(key["id"] == key_id for key in listed.json()["api_keys"])

    updated = c.patch(f"/api/v2/admin/api-keys/{key_id}", json={"is_active": False})
    assert updated.status_code == 200
    assert updated.json()["api_key"]["is_active"] is False

    revoked = c.delete(f"/api/v2/admin/api-keys/{key_id}")
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "REVOKED"


def test_mfa_setup_enable_and_verify():
    c = client()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "admin@sentinel.local").first()
        if not user:
            user = User(
                id="test-admin",
                email="admin@sentinel.local",
                full_name="Admin",
                hashed_password="unused",
                role="SUPER_ADMIN",
                department="GLOBAL_SECURITY",
                tenant_id="default",
                is_active=True,
                metadata_={},
            )
            db.add(user)
            db.commit()
    finally:
        db.close()

    setup = c.post("/api/v2/auth/mfa/setup")
    assert setup.status_code == 200
    secret = setup.json()["secret"]

    enabled = c.post("/api/v2/auth/mfa/enable", json={"code": _totp_code(secret)})
    assert enabled.status_code == 200
    assert enabled.json()["status"] == "MFA_ENABLED"

    verified = c.post("/api/v2/auth/mfa/verify", json={
        "email": "admin@sentinel.local",
        "code": _totp_code(secret),
    })
    assert verified.status_code == 200


def test_policy_simulator_and_evidence_schedule():
    c = client()
    simulation = c.post("/api/v2/policy/simulate", json={
        "prompt": "Send Aadhaar 2345 6789 0123 to cloud model",
        "department": "GLOBAL_SECURITY",
    })
    assert simulation.status_code == 200
    assert simulation.json()["findings_count"] >= 1
    assert "redacted_preview" in simulation.json()

    schedule = c.post("/api/v2/enterprise/evidence-schedule", json={
        "enabled": True,
        "frequency": "weekly",
        "org_name": "Buyer Co",
        "tenant_id": "default",
        "retention_days": 365,
    })
    assert schedule.status_code == 200
    assert schedule.json()["schedule"]["org_name"] == "Buyer Co"

    fetched = c.get("/api/v2/enterprise/evidence-schedule")
    assert fetched.status_code == 200
    assert fetched.json()["configured"] is True
