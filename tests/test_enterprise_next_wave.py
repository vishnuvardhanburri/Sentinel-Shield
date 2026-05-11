import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app import app, get_active_user, _totp_code  # noqa: E402
from auth.jwt_handler import TokenPayload  # noqa: E402
from db.models import User  # noqa: E402
from db.session import SessionLocal, init_db, pwd_context  # noqa: E402


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


def test_api_key_can_call_proxy_without_jwt():
    c = client()
    created = c.post("/api/v2/admin/api-keys", json={
        "name": "Proxy Integration",
        "scopes": ["proxy:inspect"],
        "department": "API_CLIENT",
        "expires_in_days": 30,
    })
    secret = created.json()["secret"]
    app.dependency_overrides.clear()
    try:
        response = TestClient(app).post(
            "/api/v2/proxy/inspect",
            headers={"X-Sentinel-API-Key": secret},
            json={
                "text": "Aadhaar 2345 6789 0123 needs review",
                "source_app": "crm",
                "actor": "crm-user",
                "auto_redact": True,
            },
        )
        assert response.status_code == 200
        assert "2345 6789 0123" not in response.json()["protected_text"]
    finally:
        app.dependency_overrides[get_active_user] = super_admin


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


def test_login_refresh_and_device_session_tracking():
    init_db()
    db = SessionLocal()
    email = "cross-platform-admin@sovereign.local"
    password = "TemporaryPass123!"
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                id="cross-platform-admin",
                email=email,
                full_name="Cross Platform Admin",
                hashed_password=pwd_context.hash(password),
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

    app.dependency_overrides.clear()
    try:
        c = TestClient(app)
        login = c.post("/api/v2/auth/login", json={
            "email": email,
            "password": password,
            "device": {
                "device_id": "macos-test-console",
                "platform": "macos",
                "app_version": "0.1.0",
                "device_name": "Test Desktop",
            },
        })
        assert login.status_code == 200
        body = login.json()
        assert body["tokens"]["accessToken"]
        assert body["tokens"]["refreshToken"]
        assert body["device_session"]["device_id"] == "macos-test-console"

        refresh = c.post("/api/v2/auth/refresh", json={
            "refresh_token": body["tokens"]["refreshToken"],
            "device": {
                "device_id": "macos-test-console",
                "platform": "macos",
                "app_version": "0.1.1",
            },
        })
        assert refresh.status_code == 200
        refreshed = refresh.json()
        assert refreshed["tokens"]["accessToken"] != body["tokens"]["accessToken"]
        assert refreshed["device_session"]["app_version"] == "0.1.1"

        sessions = c.get(
            "/api/v2/devices/sessions",
            headers={"Authorization": f"Bearer {refreshed['tokens']['accessToken']}"},
        )
        assert sessions.status_code == 200
        assert any(s["device_id"] == "macos-test-console" for s in sessions.json()["sessions"])
    finally:
        app.dependency_overrides[get_active_user] = super_admin


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
