"""
Sentinel Shield v2 — License Validator (Client-Side)
Used by the Sentinel backend to validate a locally saved license on startup.
Calls the license server (cloud mode) or uses offline validation (air-gap mode).
"""
import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional
try:
    from config import security_settings
except ImportError:
    from .config import security_settings

LICENSE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".vault_license_v2"))
LICENSE_SERVER_URL = os.getenv("LICENSE_SERVER_URL", "")  # Empty = air-gap offline mode
MASTER_SECRET = security_settings()["license_master_secret"]


class LicenseValidator:
    """
    Client-side license validator.
    Online: validates against the license server API.
    Offline (air-gap): validates the license record stored locally.
    """

    def load_local(self) -> Optional[Dict[str, Any]]:
        """Load the locally stored license record."""
        if not os.path.exists(LICENSE_FILE):
            return None
        try:
            with open(LICENSE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def save_local(self, record: Dict[str, Any]):
        """Save the license record locally after activation."""
        with open(LICENSE_FILE, "w") as f:
            json.dump(record, f, indent=2)

    def validate_offline(self, hardware_id: str) -> Dict[str, Any]:
        """
        Offline validation using the locally stored license record.
        Checks: key format, expiry, hardware lock.
        """
        record = self.load_local()
        if not record:
            return {"valid": False, "reason": "NO_LOCAL_LICENSE"}

        key = record.get("license_key", "")
        if not key.startswith("SNTL-"):
            return {"valid": False, "reason": "INVALID_KEY_FORMAT"}

        # Expiry check
        expires_at = record.get("expires_at")
        if expires_at:
            exp = datetime.fromisoformat(expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                return {"valid": False, "reason": "EXPIRED", "expired_at": expires_at}

        # Hardware lock (air-gap)
        locked_hw = record.get("hardware_id")
        if record.get("deployment_mode") == "airgap" and locked_hw and locked_hw != hardware_id:
            return {"valid": False, "reason": "HARDWARE_MISMATCH"}

        if not record.get("is_active", False):
            return {"valid": False, "reason": "DEACTIVATED"}

        return {
            "valid": True,
            "plan": record.get("plan", "UNKNOWN"),
            "organization": record.get("organization", "Unknown"),
            "expires_at": expires_at,
            "deployment_mode": record.get("deployment_mode", "airgap"),
        }

    def validate_online(self, license_key: str, hardware_id: str) -> Dict[str, Any]:
        """Online validation against the license server (cloud mode)."""
        if not LICENSE_SERVER_URL:
            return {"valid": False, "reason": "NO_LICENSE_SERVER_URL"}
        try:
            import requests
            resp = requests.post(
                f"{LICENSE_SERVER_URL}/license/validate",
                json={"license_key": license_key, "hardware_id": hardware_id},
                timeout=10,
            )
            return resp.json()
        except Exception as e:
            return {"valid": False, "reason": f"SERVER_UNREACHABLE: {e}"}

    def is_valid(self, hardware_id: str) -> bool:
        """Quick boolean check used at startup."""
        record = self.load_local()
        if not record:
            return False

        if LICENSE_SERVER_URL and record.get("deployment_mode") != "airgap":
            result = self.validate_online(record.get("license_key", ""), hardware_id)
        else:
            result = self.validate_offline(hardware_id)

        return result.get("valid", False)


# Singleton
license_validator = LicenseValidator()
