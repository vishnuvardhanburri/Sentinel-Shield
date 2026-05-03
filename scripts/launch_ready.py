#!/usr/bin/env python3
"""One-command localhost launcher for non-technical buyer demos."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def log(message: str):
    print(f"[Sovereign Launch] {message}", flush=True)


def port_open(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def load_env() -> dict:
    env = dict(os.environ)
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, value = stripped.split("=", 1)
                env.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    env.setdefault("PYTHONPATH", str(ROOT / "backend"))
    env.setdefault("NEXT_PUBLIC_API_URL", "http://localhost:8000")
    return env


def backend_python() -> str:
    buyer_python = ROOT / ".buyer_venv/bin/python"
    if buyer_python.exists():
        return str(buyer_python)
    for candidate in (ROOT / ".verify_venv/bin/python", ROOT / ".runtime_venv/bin/python"):
        if candidate.exists():
            try:
                version = subprocess.check_output([str(candidate), "-c", "import sys; print(sys.version_info[:2])"], text=True, timeout=5)
                if "(3, 13)" not in version and "(3, 14)" not in version:
                    return str(candidate)
            except Exception:
                pass
    try:
        subprocess.run(["python3.11", "--version"], capture_output=True, text=True, timeout=5, check=True)
        log("Creating Python 3.11 buyer runtime...")
        subprocess.run(["python3.11", "-m", "venv", str(ROOT / ".buyer_venv")], cwd=ROOT, check=True)
        subprocess.run([str(buyer_python), "-m", "pip", "install", "--upgrade", "pip"], cwd=ROOT, check=True)
        subprocess.run([str(ROOT / ".buyer_venv/bin/pip"), "install", "-r", "requirements.txt"], cwd=ROOT, check=True)
        return str(buyer_python)
    except Exception:
        pass
    return sys.executable


def run_step(name: str, command: list[str], timeout: int = 180) -> bool:
    log(f"{name}...")
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    if completed.returncode == 0:
        log(f"{name}: OK")
        return True
    log(f"{name}: FAILED")
    if completed.stdout:
        print(completed.stdout[-1500:])
    if completed.stderr:
        print(completed.stderr[-1500:])
    return False


def wait_for(port: int, label: str, timeout: int = 60) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_open(port):
            log(f"{label} is live on port {port}")
            return True
        time.sleep(0.5)
    log(f"{label} did not become ready on port {port}")
    return False


def start_backend(env: dict) -> subprocess.Popen | None:
    if port_open(8000):
        log("Backend already running at http://localhost:8000")
        return None
    python = backend_python()
    log("Starting FastAPI security gateway...")
    return subprocess.Popen(
        [python, "-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=ROOT,
        env=env,
    )


def start_frontend(env: dict) -> subprocess.Popen | None:
    if port_open(3000):
        log("Dashboard already running at http://localhost:3000")
        return None
    if not (ROOT / "frontend/node_modules").exists():
        if not run_step("Installing dashboard packages", ["pnpm", "--dir", "frontend", "install"], timeout=300):
            raise RuntimeError("Dashboard package install failed")
    log("Starting Xavira dashboard...")
    return subprocess.Popen(["pnpm", "--dir", "frontend", "dev"], cwd=ROOT, env=env)


def main() -> int:
    env = load_env()
    procs: list[subprocess.Popen] = []
    try:
        backend = start_backend(env)
        if backend:
            procs.append(backend)
        if not wait_for(8000, "API"):
            return 1

        frontend = start_frontend(env)
        if frontend:
            procs.append(frontend)
        if not wait_for(3000, "Dashboard", timeout=150):
            return 1

        smoke_python = backend_python()
        if not run_step("End-to-end smoke check", [smoke_python, "scripts/smoke_e2e.py"], timeout=120):
            return 1

        print("\nREADY TO DEMO / SUBMIT")
        print("Dashboard: http://localhost:3000")
        print("API:       http://localhost:8000")
        print("Docs:      http://localhost:8000/api/docs")
        print("\nKeep this terminal open. Press Ctrl+C to stop services started by this launcher.")

        while procs:
            time.sleep(1)
            for proc in list(procs):
                if proc.poll() is not None:
                    procs.remove(proc)
                    log("A launched service stopped. Check the output above.")
                    return proc.returncode or 1
        return 0
    except KeyboardInterrupt:
        log("Stopping launched services...")
        return 0
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
