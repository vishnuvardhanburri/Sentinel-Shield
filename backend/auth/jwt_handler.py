"""
Sovereign Shield v2 — JWT Authentication Handler
Handles JWT token creation, validation, and refresh for enterprise users.
"""
import os
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
try:
    from config import security_settings
except ImportError:
    from ..config import security_settings

JWT_SECRET = security_settings()["jwt_secret"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "8"))
JWT_REFRESH_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "7"))

security_scheme = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    sub: str          # user_id
    email: str
    role: str
    department: Optional[str] = None
    tenant_id: Optional[str] = "default"
    force_password_change: bool = False
    exp: Optional[int] = None
    iat: Optional[int] = None
    jti: Optional[str] = None


class JWTHandler:
    """Enterprise JWT handler with role + tenant awareness."""

    def create_access_token(self, data: Dict[str, Any], expires_hours: Optional[int] = None) -> str:
        """Creates a signed JWT access token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(hours=expires_hours or JWT_EXPIRY_HOURS)
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(24),
            "type": "access"
        })
        return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Creates a long-lived refresh token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_DAYS)
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": secrets.token_urlsafe(24),
            "type": "refresh"
        })
        return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str) -> TokenPayload:
        """Validates a JWT and returns the decoded payload."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "access":
                raise HTTPException(status_code=401, detail="Invalid token type")
            jti = payload.get("jti")
            if jti and is_token_revoked(jti):
                raise HTTPException(status_code=401, detail="Token revoked")
            return TokenPayload(
                sub=payload.get("sub", ""),
                email=payload.get("email", ""),
                role=payload.get("role", "STAFF"),
                department=payload.get("department"),
                tenant_id=payload.get("tenant_id", "default"),
                force_password_change=bool(payload.get("force_password_change", False)),
                exp=payload.get("exp"),
                iat=payload.get("iat"),
                jti=jti,
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def verify_refresh_token(self, token: str) -> TokenPayload:
        """Validates a refresh token and returns the decoded payload."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="Invalid token type")
            jti = payload.get("jti")
            if jti and is_token_revoked(jti):
                raise HTTPException(status_code=401, detail="Token revoked")
            return TokenPayload(
                sub=payload.get("sub", ""),
                email=payload.get("email", ""),
                role=payload.get("role", "STAFF"),
                department=payload.get("department"),
                tenant_id=payload.get("tenant_id", "default"),
                force_password_change=bool(payload.get("force_password_change", False)),
                exp=payload.get("exp"),
                iat=payload.get("iat"),
                jti=jti,
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def get_current_user(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)
    ) -> TokenPayload:
        """FastAPI dependency to extract and validate the current user from the Bearer header."""
        if not credentials:
            raise HTTPException(status_code=401, detail="No authorization credentials provided")
        return self.verify_token(credentials.credentials)


# Module-level singletons and convenience functions
_handler = JWTHandler()
_REVOKED_JTIS = set()
_REDIS_CLIENT = None


def _redis_client():
    global _REDIS_CLIENT
    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        return None
    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT
    try:
        import redis
        _REDIS_CLIENT = redis.Redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1)
        _REDIS_CLIENT.ping()
        return _REDIS_CLIENT
    except Exception:
        _REDIS_CLIENT = None
        return None


def revoke_token_id(jti: str, exp: Optional[int] = None):
    if jti:
        client = _redis_client()
        if client:
            ttl = 60 * 60 * 24
            if exp:
                ttl = max(60, int(exp - datetime.now(timezone.utc).timestamp()))
            client.setex(f"sentinel:revoked_jti:{jti}", ttl, "1")
        _REVOKED_JTIS.add(jti)


def is_token_revoked(jti: str) -> bool:
    client = _redis_client()
    if client and client.get(f"sentinel:revoked_jti:{jti}") == "1":
        return True
    return jti in _REVOKED_JTIS


def create_access_token(data: Dict[str, Any], expires_hours: Optional[int] = None) -> str:
    return _handler.create_access_token(data, expires_hours)


def create_refresh_token(data: Dict[str, Any]) -> str:
    return _handler.create_refresh_token(data)


def verify_token(token: str) -> TokenPayload:
    return _handler.verify_token(token)


def verify_refresh_token(token: str) -> TokenPayload:
    return _handler.verify_refresh_token(token)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)
) -> TokenPayload:
    return _handler.get_current_user(credentials)
