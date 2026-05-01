"""
Sentinel Shield v2 — Audit Ledger Tests
Tests the hash chain integrity, tamper detection, and export functions.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

import pytest
import tempfile
import json
from audit.ledger import AuditLedger
from audit.hash_chain import HashChain


class TestHashChain:
    def test_hash_entry_is_deterministic(self):
        entry = {"action": "QUERY", "user_id": "user1", "timestamp": "2026-01-01"}
        h1 = HashChain.hash_entry(entry)
        h2 = HashChain.hash_entry(entry)
        assert h1 == h2

    def test_hash_entry_excludes_entry_hash(self):
        entry = {"action": "QUERY", "user_id": "user1", "entry_hash": "abc123"}
        entry_no_hash = {"action": "QUERY", "user_id": "user1"}
        assert HashChain.hash_entry(entry) == HashChain.hash_entry(entry_no_hash)

    def test_different_entries_produce_different_hashes(self):
        e1 = {"action": "QUERY", "user_id": "user1"}
        e2 = {"action": "QUERY", "user_id": "user2"}
        assert HashChain.hash_entry(e1) != HashChain.hash_entry(e2)

    def test_hash_text(self):
        h = HashChain.hash_text("test prompt")
        assert len(h) == 64  # SHA-256 hex

    def test_hash_bytes(self):
        h = HashChain.hash_bytes(b"test data")
        assert len(h) == 64


class TestAuditLedger:
    @pytest.fixture
    def ledger(self, tmp_path):
        ledger_file = str(tmp_path / "audit_ledger.jsonl")
        return AuditLedger(ledger_path=ledger_file)

    def test_single_entry_chain_valid(self, ledger):
        entry_hash = ledger.log(
            action="AI_QUERY",
            user_id="user_001",
            user_role="STAFF",
            department="ICU",
        )
        entry = ledger.get_entries(limit=1)[0]
        assert entry["signature"] == entry_hash
        assert len(entry["actor_hash"]) == 64
        result = ledger.verify_chain()
        assert result["valid"] is True

    def test_multiple_entries_chain_valid(self, ledger):
        for i in range(5):
            ledger.log(
                action=f"ACTION_{i}",
                user_id=f"user_{i}",
                user_role="STAFF",
            )
        result = ledger.verify_chain()
        assert result["valid"] is True
        assert result["total_entries"] == 5

    def test_tampered_entry_fails_verification(self, ledger):
        ledger.log(action="QUERY", user_id="user1", user_role="STAFF")
        ledger.log(action="EXPORT", user_id="admin", user_role="AUDITOR")

        # Tamper: rewrite first entry content
        with open(ledger.ledger_path, "r") as f:
            lines = f.readlines()

        first = json.loads(lines[0])
        first["action"] = "HACKED"  # Tamper the content
        lines[0] = json.dumps(first) + "\n"

        with open(ledger.ledger_path, "w") as f:
            f.writelines(lines)

        result = ledger.verify_chain()
        assert result["valid"] is False
        assert result["corrupted_at"] is not None

    def test_get_entries_returns_newest_first(self, ledger):
        for i in range(3):
            ledger.log(action=f"ACT_{i}", user_id="user1", user_role="STAFF")
        entries = ledger.get_entries(limit=10)
        assert entries[0]["action"] == "ACT_2"  # newest first

    def test_filter_by_user(self, ledger):
        ledger.log(action="A", user_id="alice", user_role="STAFF")
        ledger.log(action="B", user_id="bob",   user_role="STAFF")
        ledger.log(action="C", user_id="alice", user_role="STAFF")
        entries = ledger.get_entries(limit=10, user_id="alice")
        assert all(e["user_id"] == "alice" for e in entries)
        assert len(entries) == 2

    def test_filter_by_department(self, ledger):
        ledger.log(action="A", user_id="u1", user_role="STAFF", department="ICU")
        ledger.log(action="B", user_id="u2", user_role="STAFF", department="LEGAL")
        entries = ledger.get_entries(limit=10, department="ICU")
        assert all(e["department"] == "ICU" for e in entries)

    def test_empty_ledger_chain_valid(self, ledger):
        result = ledger.verify_chain()
        assert result["valid"] is True
        assert result["total_entries"] == 0

    def test_summary_stats(self, ledger):
        for i in range(3):
            ledger.log(
                action="AI_QUERY",
                user_id="user1",
                user_role="STAFF",
                redactions_applied=["REDACTED_SSN", "REDACTED_AADHAAR"],
                risk_score=float(i + 1),
            )
        stats = ledger.get_summary_stats()
        assert stats["total_events"] == 3
        assert stats["total_redactions"] == 6
