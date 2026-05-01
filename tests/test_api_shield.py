from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from backend.api_shield import InMemoryRateCostLimiter, ZeroTrustAPIShieldMiddleware


async def ok_endpoint(request):
    return JSONResponse({"ok": True})


def build_client(**middleware_kwargs):
    app = Starlette(routes=[
        Route("/ask", ok_endpoint, methods=["POST"]),
        Route("/health", ok_endpoint, methods=["GET"]),
        Route("/.env", ok_endpoint, methods=["GET"]),
    ])
    app.add_middleware(ZeroTrustAPIShieldMiddleware, **middleware_kwargs)
    return TestClient(app)


def test_security_headers_are_added_to_unprotected_routes():
    client = build_client()
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"


def test_suspicious_paths_are_blocked_before_routing():
    client = build_client()
    response = client.get("/.env")

    assert response.status_code == 404
    assert response.json()["detail"] == "NOT_FOUND"


def test_large_protected_requests_are_rejected():
    client = build_client()
    response = client.post("/ask", content="x" * 32, headers={"content-length": "999999"})

    assert response.status_code == 413
    assert response.json()["detail"] == "REQUEST_TOO_LARGE"


def test_mtls_enforcement_requires_verified_certificate_headers():
    client = build_client(enforce_mtls=True)
    denied = client.post("/ask", json={"prompt": "hello"})
    allowed = client.post(
        "/ask",
        json={"prompt": "hello"},
        headers={
            "x-ssl-client-verify": "SUCCESS",
            "x-ssl-client-fingerprint": "abc123",
        },
    )

    assert denied.status_code == 401
    assert denied.json()["detail"] == "MTLS_CLIENT_CERT_REQUIRED"
    assert allowed.status_code == 200


def test_rate_limiter_blocks_repeated_protected_requests():
    limiter = InMemoryRateCostLimiter(max_requests=1, window_seconds=60, max_cost_usd=5.0)
    client = build_client(limiter=limiter)

    first = client.post("/ask", json={"prompt": "hello"}, headers={"authorization": "Bearer one"})
    second = client.post("/ask", json={"prompt": "hello"}, headers={"authorization": "Bearer one"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "RATE_LIMIT_EXCEEDED"
