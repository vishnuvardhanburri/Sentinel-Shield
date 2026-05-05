"""
Sovereign Shield v2 — Hash Chain Utilities
SHA-256 chaining primitives used by the AuditLedger.
"""
import hashlib
import json
from typing import Any, Dict


class HashChain:
    """Stateless SHA-256 hash chain helper."""

    @staticmethod
    def hash_entry(entry: Dict[str, Any]) -> str:
        """Produce a deterministic SHA-256 hash of a dict (excluding entry_hash)."""
        payload = {k: v for k, v in entry.items() if k != "entry_hash"}
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(canonical.encode()).hexdigest()

    @staticmethod
    def hash_text(text: str) -> str:
        """Hash arbitrary text — used for prompt hashing."""
        return hashlib.sha256(text.encode()).hexdigest()

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        """Hash raw bytes — used for document integrity."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def verify_chain_link(prev_entry: Dict[str, Any], current_entry: Dict[str, Any]) -> bool:
        """
        Verify that current_entry.prev_hash == prev_entry.entry_hash.
        Returns True if the link is valid.
        """
        expected_prev = prev_entry.get("entry_hash", "")
        actual_prev = current_entry.get("prev_hash", "")
        return expected_prev == actual_prev
