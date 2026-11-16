"""Supervise a temporary HTTPS tunnel to an isolated local TenderGuard server.

No AWS resources or Windows services are created. The existing local demo is left
alone. Credentials are generated into an owner-only local folder and never printed.
"""

import argparse
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "storage" / "temporary_demo"
URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com\b")


def private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=False, mode=0o700)
    if os.name == "nt":
        identity = subprocess.run(
            ["whoami", "/user", "/fo", "csv", "/nh"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        match = re.search(r"S-1-[0-9-]+", identity)
        if match is None:
            raise RuntimeError("Could not determine the Windows credential-file owner.")
        subprocess.run(
            [
                "icacls",
                str(path),
                "/inheritance:r",
                "/grant:r",
                f"*{match.group(0)}:(OI)(CI)F",
                "*S-1-5-18:(OI)(CI)F",
                "/remove:g",
                "*S-1-5-32-544",
                "*S-1-3-4",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )


def write_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(path)


def current_run() -> Path:
    record = json.loads((RUNTIME / "latest.json").read_text(encoding="utf-8"))
    run = (RUNTIME / record["run_id"]).resolve()
    if run.parent != RUNTIME.resolve() or not re.fullmatch(r"run-[a-f0-9]{16}", run.name):
        raise ValueError("Invalid temporary-demo runtime boundary.")
    return run


def stop_process(process: subprocess.Popen | None) -> None:
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def serve(cloudflared: Path, port: int, hours: float) -> None:
    if not 0 < hours <= 8 or not 1024 <= port <= 65535:
        raise ValueError(
            "Use a free local port and a duration greater than zero, up to eight hours."
        )
    if not cloudflared.resolve(strict=True).is_file():
        raise ValueError("The verified cloudflared executable is missing.")
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise RuntimeError("Build the existing frontend before starting the temporary demo.")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))
    RUNTIME.mkdir(parents=True, exist_ok=True)
    run = RUNTIME / f"run-{secrets.token_hex(8)}"
    private_directory(run)
    write_json(RUNTIME / "latest.json", {"run_id": run.name})
    password = secrets.token_urlsafe(32)
    password_file = run / "dashboard-password.txt"
    password_file.write_text(password, encoding="utf-8")
    password_file.chmod(0o600)
    expires = datetime.now(UTC) + timedelta(hours=hours)
    state = {
        "status": "STARTING",
        "expires_at": expires.isoformat(),
        "credential_file": str(password_file),
        "run_id": run.name,
    }
    write_json(run / "status.json", state)
    tunnel = server = None
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        with (
            (run / "tunnel.log").open("w", encoding="utf-8") as tunnel_log,
            (run / "server.log").open("w", encoding="utf-8") as server_log,
        ):
            tunnel = subprocess.Popen(
                [
                    str(cloudflared.resolve()),
                    "tunnel",
                    "--no-autoupdate",
                    "--url",
                    f"http://127.0.0.1:{port}",
                    "--protocol",
                    "http2",
                ],
                stdout=tunnel_log,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags,
            )
            url = None
            for _ in range(90):
                if tunnel.poll() is not None:
                    raise RuntimeError("The temporary tunnel exited before becoming ready.")
                log = (run / "tunnel.log").read_text(encoding="utf-8", errors="replace")
                match = URL_PATTERN.search(log)
                if match:
                    url = match.group(0)
                    break
                time.sleep(1)
            if url is None:
                raise RuntimeError("No temporary HTTPS hostname was issued.")
            environment = {
                **os.environ,
                "TENDERGUARD_API_KEY": secrets.token_urlsafe(48),
                "TENDERGUARD_DASHBOARD_PASSWORD": password,
                "TENDERGUARD_ALLOWED_ORIGINS": url,
                "TENDERGUARD_COOKIE_SECURE": "true",
                "TENDERGUARD_DOCUMENT_STORAGE": str(run / "document_evaluations"),
                "TENDERGUARD_OLLAMA_URL": "http://127.0.0.1:11434/api/chat",
                "TENDERGUARD_OLLAMA_MODEL": "qwen3:1.7b",
            }
            server = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.api.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--no-access-log",
                    "--no-server-header",
                ],
                cwd=ROOT,
                env=environment,
                stdout=server_log,
                stderr=subprocess.STDOUT,
                creationflags=creation_flags,
            )
            for _ in range(60):
                if server.poll() is not None:
                    raise RuntimeError("The isolated backend exited during startup.")
                try:
                    with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
                        if response.status == 200:
                            break
                except OSError:
                    pass
                time.sleep(1)
            else:
                raise RuntimeError("The isolated backend did not become ready.")
            state.update(status="RUNNING", url=url, port=port, supervisor_pid=os.getpid())
            write_json(run / "status.json", state)
            print(f"Temporary HTTPS demo ready: {url}", flush=True)
            while datetime.now(UTC) < expires and not (run / "STOP").exists():
                if tunnel.poll() is not None or server.poll() is not None:
                    raise RuntimeError("A temporary-demo process exited.")
                time.sleep(1)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        state.update(status="FAILED", error_type=type(exc).__name__)
        write_json(run / "status.json", state)
        raise
    finally:
        stop_process(tunnel)
        stop_process(server)
        if state["status"] != "FAILED":
            state["status"] = "STOPPED"
            write_json(run / "status.json", state)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cloudflared", type=Path)
    parser.add_argument("--port", type=int, default=8768)
    parser.add_argument("--hours", type=float, default=8)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()
    if args.status:
        print((current_run() / "status.json").read_text(encoding="utf-8"))
    elif args.stop:
        (current_run() / "STOP").touch()
        print("Stop requested for the temporary demo only.")
    elif args.cloudflared:
        serve(args.cloudflared, args.port, args.hours)
    else:
        parser.error("Provide --cloudflared, --status, or --stop.")


if __name__ == "__main__":
    main()
