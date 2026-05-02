"""License enforcement middleware stub for future SaaS/commercial deployments."""
import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class LicenseValidationMiddleware(BaseHTTPMiddleware):
    """Fail-closed middleware when SENTINEL_LICENSE_ENFORCEMENT=true.

    This is intentionally lightweight for acquisition demos. Production buyers can
    connect it to the bundled license server, Stripe, Lemon Squeezy, or an
    enterprise entitlement service.
    """

    async def dispatch(self, request, call_next):
        enforce = os.getenv("SENTINEL_LICENSE_ENFORCEMENT", "false").lower() == "true"
        if not enforce:
            return await call_next(request)
        exempt = {"/", "/health", "/api/docs", "/api/v1/license/validate"}
        if request.url.path in exempt or request.url.path.startswith("/api/redoc"):
            return await call_next(request)
        if os.getenv("SENTINEL_LICENSE_KEY"):
            return await call_next(request)
        return JSONResponse(
            {"detail": "LICENSE_REQUIRED", "endpoint": "/api/v1/license/validate"},
            status_code=402,
        )
