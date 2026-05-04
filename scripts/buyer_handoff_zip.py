#!/usr/bin/env python3
"""Build a buyer handoff ZIP with docs, certificates, and deployment artifacts."""
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "logs" / "handoff"
OUT.mkdir(parents=True, exist_ok=True)


def run_optional(command: list[str]):
    subprocess.run(command, cwd=ROOT, check=False)


def add_if_exists(archive: zipfile.ZipFile, path: Path, arcname: str | None = None):
    if path.is_file():
        archive.write(path, arcname or str(path.relative_to(ROOT)))


def latest_files(folder: Path, patterns: tuple[str, ...], limit: int = 8) -> list[Path]:
    if not folder.exists():
        return []
    files: list[Path] = []
    for pattern in patterns:
        files.extend(path for path in folder.glob(pattern) if path.is_file())
    unique = {path.resolve(): path for path in files}
    return sorted(unique.values(), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]


def main() -> int:
    run_optional(["python3", "scripts/generate_deployment_pack.py"])
    run_optional(["python3", "scripts/generate_handoff_pdf.py"])
    run_optional(["python3", "scripts/production_readiness_certificate.py"])

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    zip_path = OUT / f"sovereign_shield_buyer_handoff_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in ["README.md", "DOCS.md", "SECURITY.md", "RELEASE.md", "SUBMISSION_CHECKLIST.md", ".env.example.production", "release.json"]:
            add_if_exists(zf, ROOT / name)
        for folder, patterns in [
            (ROOT / "logs" / "deployment_pack", ("*.json", "*.md", "*.txt", "*.pdf")),
            (ROOT / "logs" / "certificates", ("*.json", "*.pdf")),
            (ROOT / "logs" / "handoff", ("*.pdf", "*.json")),
            (ROOT / "logs" / "exports", ("*.pdf", "*.json")),
            (ROOT / "logs" / "demo", ("*.jsonl",)),
        ]:
            for path in latest_files(folder, patterns):
                if path != zip_path and path.suffix != ".zip":
                    zf.write(path, str(path.relative_to(ROOT)))
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    manifest = {
        "file": str(zip_path),
        "sha256": digest,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "excludes": [".env", "sentinel.db", "logs containing runtime secrets"],
    }
    manifest_path = OUT / f"handoff_manifest_{stamp}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
