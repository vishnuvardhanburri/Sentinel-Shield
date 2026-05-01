"""
Sentinel Shield Enterprise — Zero-Trust API Shield

FastAPI middleware for service-to-service mTLS enforcement, rate limiting, and
cost controls. In production, terminate TLS at Envoy/Nginx and forward verified
client certificate metadata in locked-down headers.
"""
import os
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class BudgetState:
    window_started: float
    requests: int = 0
    estimated_cost_usd: float = 0.0


class InMemoryRateCostLimiter:
    def __init__(self, max_requests: int = 120, window_seconds: int = 60, max_cost_usd: float = 5.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.max_cost_usd = max_cost_usd
        self._buckets: Dict[str, BudgetState] = {}

    def check(self, actor_key: str, estimated_cost_usd: float = 0.0) -> Tuple[bool, str]:
        now = time.time()
        bucket = self._buckets.get(actor_key)
        if not bucket or now - bucket.window_started > self.window_seconds:
            bucket = BudgetState(window_started=now)
            self._buckets[actor_key] = bucket

        if bucket.requests + 1 > self.max_requests:
            return False, "RATE_LIMIT_EXCEEDED"
        if bucket.estimated_cost_usd + estimated_cost_usd > self.max_cost_usd:
            return False, "COST_BUDGET_EXCEEDED"

        bucket.requests += 1
        bucket.estimated_cost_usd += estimated_cost_usd
        return True, "OK"


class ZeroTrustAPIShieldMiddleware(BaseHTTPMiddleware):
    """
    Enforces mTLS metadata and request budget controls.

    Expected headers from trusted TLS terminator:
      x-ssl-client-verify: SUCCESS
      x-ssl-client-fingerprint: <sha256 cert fingerprint>
    """

    def __init__(
        self,
        app,
        limiter: Optional[InMemoryRateCostLimiter] = None,
        enforce_mtls: Optional[bool] = None,
    ):
        super().__init__(app)
        self.limiter = limiter or InMemoryRateCostLimiter(
            max_requests=int(os.getenv("API_SHIELD_MAX_REQUESTS", "120")),
            window_seconds=int(os.getenv("API_SHIELD_WINDOW_SECONDS", "60")),
            max_cost_usd=float(os.getenv("API_SHIELD_MAX_COST_USD", "5.0")),
        )
        self.enforce_mtls = (
            os.getenv("API_SHIELD_ENFORCE_MTLS", "false").lower() == "true"
            if enforce_mtls is None
            else enforce_mtls
        )
        self.protected_prefixes = tuple(
            prefix.strip()
            for prefix in os.getenv("API_SHIELD_PROTECTED_PREFIXES", "/ask,/api/v2/chat").split(",")
            if prefix.strip()
        )

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith(self.protected_prefixes):
            return await call_next(request)

        cert_fingerprint = self._require_mtls(request)
        actor_key = cert_fingerprint or request.headers.get("authorization", request.client.host if request.client else "unknown")
        estimated_cost = self._estimate_request_cost(request)
        allowed, reason = self.limiter.check(actor_key=actor_key, estimated_cost_usd=estimated_cost)
        if not allowed:
            raise HTTPException(status_code=429, detail=reason)

        return await call_next(request)

    def _require_mtls(self, request: Request) -> Optional[str]:
        verified = request.headers.get("x-ssl-client-verify", "")
        fingerprint = request.headers.get("x-ssl-client-fingerprint")
        if self.enforce_mtls and (verified.upper() != "SUCCESS" or not fingerprint):
            raise HTTPException(status_code=401, detail="MTLS_CLIENT_CERT_REQUIRED")
        return fingerprint

    @staticmethod
    def _estimate_request_cost(request: Request) -> float:
        token_header = request.headers.get("x-estimated-tokens")
        try:
            tokens = max(0, int(token_header or "0"))
        except ValueError:
            tokens = 0
        return (tokens / 1000.0) * float(os.getenv("API_SHIELD_COST_PER_1K_TOKENS", "0.01"))
