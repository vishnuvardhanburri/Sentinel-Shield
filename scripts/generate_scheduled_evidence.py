#!/usr/bin/env python3
"""Generate scheduled Sentinel Shield evidence PDFs from local schedule files."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from reporting.evidence_report import EvidencePDFGenerator  # noqa: E402


def main() -> int:
    schedule_dir = ROOT / "logs" / "schedules"
    if not schedule_dir.exists():
        print("No evidence schedules configured.")
        return 0

    generator = EvidencePDFGenerator()
    generated = []
    for path in schedule_dir.glob("evidence_schedule_*.json"):
        schedule = json.loads(path.read_text())
        if not schedule.get("enabled", True):
            continue
        result = generator.generate(
            org_name=schedule.get("org_name", "Buyer Organization"),
            tenant_id=schedule.get("tenant_id", "default"),
            limit=1000,
            compliance_frameworks=["DPDP_2026", "GDPR", "FedRAMP"],
        )
        generated.append(result.get("file"))

    print(json.dumps({"generated": generated, "count": len(generated)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
