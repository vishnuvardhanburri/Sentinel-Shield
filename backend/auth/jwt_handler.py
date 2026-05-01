"""
Sentinel Shield v2 — JWT Authentication Handler
Handles JWT token creation, validation, and refresh for enterprise users.
"""
import os
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


class JWTHandler:
    """Enterprise JWT handler with role + tenant awareness."""

    def create_access_token(self, data: Dict[str, Any], expires_hours: Optional[int] = None) -> str:
        """Creates a signed JWT access token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(hours=expires_hours or JWT_EXPIRY_HOURS)
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
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
            "type": "refresh"
        })
        return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str) -> TokenPayload:
        """Validates a JWT and returns the decoded payload."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return TokenPayload(
                sub=payload.get("sub", ""),
                email=payload.get("email", ""),
                role=payload.get("role", "STAFF"),
                department=payload.get("department"),
                tenant_id=payload.get("tenant_id", "default"),
                force_password_change=bool(payload.get("force_password_change", False)),
                exp=payload.get("exp"),
                iat=payload.get("iat"),
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


def create_access_token(data: Dict[str, Any], expires_hours: Optional[int] = None) -> str:
    return _handler.create_access_token(data, expires_hours)


def create_refresh_token(data: Dict[str, Any]) -> str:
    return _handler.create_refresh_token(data)


def verify_token(token: str) -> TokenPayload:
    return _handler.verify_token(token)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)
) -> TokenPayload:
    return _handler.get_current_user(credentials)
