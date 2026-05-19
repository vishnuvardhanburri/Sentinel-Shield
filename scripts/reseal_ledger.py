#!/usr/bin/env python3
"""Archive a corrupted active audit ledger and start a fresh sealed chain."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    import sys

    sys.path.insert(0, str(ROOT / "backend"))
    from audit.ledger import audit_ledger

    result = audit_ledger.reseal_corrupted_chain(
        triggered_by="system-maintenance",
        user_role="SUPER_ADMIN",
        tenant_id="default",
        reason="LEDGER_MASTER_SALT_ROTATION_OR_FORENSIC_RESEAL",
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("chain_status_after", {}).get("valid", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
