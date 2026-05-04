"""
Sentinel Shield — fail-closed production configuration.

Security-sensitive values must be present and non-placeholder. This module is
imported during app boot and by license/JWT modules, so missing secrets stop the
process before any API surface is exposed.
"""
import logging
import os
from pathlib import Path
from functools import lru_cache
from typing import Iterable, List

logger = logging.getLogger("sentinel.config")
BASE_DIR = Path(__file__).resolve().parent.parent


def load_dotenv_file(path: Path = BASE_DIR / ".env"):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv_file()

PLACEHOLDER_VALUES = {
    "",
    "default",
    "changeme",
    "change_me",
    "change-me",
    "CHANGE_ME",
    "CHANGE_ME_USE_SECRETS_TOKEN_HEX_32",
    "XAVIRA TECH LABS_SENTINEL_MASTER_2026",
    "SENTINEL_SHIELD_V2_DEFAULT_AIRGAP",
    "sentinel-local-dev",
    "your-secret-here",
    "placeholder",
    "null",
    "none",
}


class SecurityConfigurationError(RuntimeError):
    """Raised when a required production security control is missing."""


def require_secret(name: str, *, min_length: int = 32, forbidden: Iterable[str] = ()) -> str:
    value = os.getenv(name, "").strip()
    invalid_values = PLACEHOLDER_VALUES | {v.strip() for v in forbidden}
    if value in invalid_values or value.lower() in {v.lower() for v in invalid_values}:
        _critical(name, "missing or placeholder value")
    if len(value) < min_length:
        _critical(name, f"too short; require at least {min_length} characters")
    return value


def allowed_origins() -> List[str]:
    raw = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,https://sentinel-shield.xaviratechlabs.com",
    )
    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    if "*" in origins:
        raise SecurityConfigurationError("CRITICAL: ALLOWED_ORIGINS cannot contain wildcard '*' in production.")
    return origins


@lru_cache(maxsize=1)
def security_settings() -> dict:
    return {
        "jwt_secret": require_secret("JWT_SECRET_KEY", min_length=48),
        "license_master_secret": require_secret("LICENSE_MASTER_SECRET", min_length=48),
        "actor_hash_salt": require_secret("ACTOR_HASH_SALT", min_length=32),
        "ledger_master_salt": require_secret("LEDGER_MASTER_SALT", min_length=32),
        "allowed_origins": allowed_origins(),
    }


def _critical(name: str, reason: str):
    message = f"CRITICAL: Security Secret Missing or Invalid: {name} ({reason})"
    logger.critical(message)
    raise SecurityConfigurationError(message)
