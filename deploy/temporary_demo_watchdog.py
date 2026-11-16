"""Adopt a legacy Windows demo watchdog while leaving its live services untouched.

Process handles pin identity across PID reuse. Only the verified old watchdog is
terminated during takeover. Its existing tunnel and server stop at the new deadline.
"""

import argparse
import ctypes
import json
import os
import subprocess
import time
from ctypes import wintypes
from datetime import UTC, datetime, timedelta
from pathlib import Path

from deploy.temporary_demo import (
    ROOT,
    current_run,
    parse_deadline,
    read_deadline,
    requested_deadline,
    write_json,
)


class WindowsProcess:
    def __init__(self, pid: int, expected_image: str, expected_started: str | None = None):
        if os.name != "nt":
            raise RuntimeError("Live watchdog takeover is implemented for Windows only.")
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.api.OpenProcess.restype = wintypes.HANDLE
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.CloseHandle.restype = wintypes.BOOL
        self.api.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.api.QueryFullProcessImageNameW.restype = wintypes.BOOL
        self.api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.api.WaitForSingleObject.restype = wintypes.DWORD
        self.api.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.api.TerminateProcess.restype = wintypes.BOOL
        self.api.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
            ctypes.POINTER(wintypes.FILETIME)
        ] * 4
        self.api.GetProcessTimes.restype = wintypes.BOOL
        # Query limited information, synchronization, and termination only.
        self.handle = self.api.OpenProcess(0x1000 | 0x100000 | 0x0001, False, pid)
        if not self.handle:
            raise OSError("Could not open the specific demo process.")
        self.pid = pid
        try:
            size = wintypes.DWORD(32768)
            image = ctypes.create_unicode_buffer(size.value)
            if not self.api.QueryFullProcessImageNameW(self.handle, 0, image, ctypes.byref(size)):
                raise OSError("Could not verify the demo process executable.")
            if Path(image.value).resolve() != Path(expected_image).resolve() or not self.alive():
                raise ValueError("Demo process identity mismatch; takeover refused.")
            created, exited, kernel, user = (wintypes.FILETIME() for _ in range(4))
            if not self.api.GetProcessTimes(
                self.handle,
                ctypes.byref(created),
                ctypes.byref(exited),
                ctypes.byref(kernel),
                ctypes.byref(user),
            ):
                raise OSError("Could not verify process creation time.")
            ticks = (created.dwHighDateTime << 32) | created.dwLowDateTime
            started = datetime(1601, 1, 1, tzinfo=UTC) + timedelta(microseconds=ticks // 10)
            if (
                expected_started
                and abs((started - parse_deadline(expected_started)).total_seconds()) > 0.001
            ):
                raise ValueError("The demo PID was reused; takeover refused.")
        except Exception:
            self.close()
            raise

    def alive(self) -> bool:
        result = self.api.WaitForSingleObject(self.handle, 0)
        if result not in {0, 258}:
            raise OSError("Could not check the pinned process handle.")
        return result == 258

    def terminate(self) -> None:
        if self.alive():
            if not self.api.TerminateProcess(self.handle, 0):
                raise OSError("Could not stop the specific demo process.")
            if self.api.WaitForSingleObject(self.handle, 10000) != 0:
                raise OSError("The specific demo process did not stop.")

    def close(self) -> None:
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def process_records(pid: int) -> list[dict]:
    if pid <= 0:
        raise ValueError("A specific live demo PID is required.")
    command = (
        "$ErrorActionPreference='Stop'; "
        f"Get-CimInstance Win32_Process -Filter 'ProcessId = {int(pid)} OR ParentProcessId = {int(pid)}'"
        " | Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine,"
        "@{Name='CreatedAt';Expression={$_.CreationDate.ToUniversalTime().ToString('o')}}"
        " | ConvertTo-Json -Depth 3 -Compress"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    records = json.loads(result.stdout)
    return records if isinstance(records, list) else [records]


def open_services(state: dict) -> tuple[WindowsProcess, list[WindowsProcess]]:
    """Discover only the recorded legacy watchdog and its exact demo children."""
    old_pid = int(state["supervisor_pid"])
    records = process_records(old_pid)
    old = next(record for record in records if record["ProcessId"] == old_pid)
    if "-m deploy.temporary_demo " not in old["CommandLine"]:
        raise ValueError("The recorded PID is not the legacy temporary-demo watchdog.")
    children = [record for record in records if record["ParentProcessId"] == old_pid]
    tunnels = [
        record
        for record in children
        if " tunnel --no-autoupdate --url " in (record["CommandLine"] or "")
    ]
    servers = [
        record
        for record in children
        if "-m uvicorn app.api.main:app " in (record["CommandLine"] or "")
    ]
    if len(tunnels) != 1 or len(servers) != 1:
        raise ValueError("Expected exactly one existing demo tunnel and backend.")
    tunnel, server = tunnels[0], servers[0]
    if f"http://127.0.0.1:{int(state['port'])}" not in tunnel["CommandLine"]:
        raise ValueError("The tunnel does not target the recorded local demo port.")
    if f"--host 127.0.0.1 --port {int(state['port'])}" not in server["CommandLine"]:
        raise ValueError("The backend does not match the recorded loopback demo port.")
    if not Path(tunnel["ExecutablePath"]).resolve().is_relative_to(ROOT):
        raise ValueError("The tunnel executable is outside the demo workspace.")
    service_records = [tunnel, server]
    # Windows venv launchers delegate to a second Python process; pin that too.
    delegated = [
        record
        for record in process_records(server["ProcessId"])
        if record["ParentProcessId"] == server["ProcessId"]
        and "-m uvicorn app.api.main:app " in (record["CommandLine"] or "")
    ]
    service_records.extend(delegated)
    opened = []
    try:
        old_handle = WindowsProcess(old_pid, old["ExecutablePath"], old["CreatedAt"])
        opened.append(old_handle)
        services = []
        for record in service_records:
            process = WindowsProcess(
                record["ProcessId"], record["ExecutablePath"], record["CreatedAt"]
            )
            services.append(process)
            opened.append(process)
        return old_handle, services
    except Exception:
        for process in opened:
            process.close()
        raise


def supervise(run: Path, state: dict, deadline: datetime, old, services: list) -> None:
    """Transfer only the watchdog; never stop live services on a controller error."""
    if not all(process.alive() for process in [old, *services]):
        raise RuntimeError("A demo process exited before watchdog takeover.")
    if (run / "STOP").exists():
        raise RuntimeError("An explicit stop request is pending; takeover refused.")
    write_json(run / "status-before-extension.json", state)
    write_json(run / "deadline.json", {"run_id": run.name, "expires_at": deadline.isoformat()})
    # Every existing service has a pinned handle before retiring the old watchdog.
    # Windows terminates this process alone; its Python finally block does not run.
    old.terminate()
    state = {
        **state,
        "expires_at": deadline.isoformat(),
        "previous_supervisor_pid": old.pid,
        "supervisor_pid": os.getpid(),
        "service_pids": [process.pid for process in services],
        "control_version": 1,
    }
    try:
        while True:
            deadline = read_deadline(run, deadline)
            state.update(
                expires_at=deadline.isoformat(), heartbeat_at=datetime.now(UTC).isoformat()
            )
            write_json(run / "status.json", state)
            if datetime.now(UTC) >= deadline or (run / "STOP").exists():
                # Stop actual Python workers before their venv launcher, plus the tunnel.
                for process in reversed(services):
                    process.terminate()
                state["status"] = "STOPPED"
                write_json(run / "status.json", state)
                return
            time.sleep(1)
    finally:
        # Closing handles never terminates services. A controller error must not
        # interrupt an active presentation; status/heartbeat makes it observable.
        for process in [old, *services]:
            process.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--until", required=True)
    parser.add_argument("--expected-supervisor", required=True, type=int)
    args = parser.parse_args()
    deadline = requested_deadline(args.until)
    run = current_run()
    state = json.loads((run / "status.json").read_text(encoding="utf-8"))
    if (
        state.get("status") != "RUNNING"
        or state.get("control_version") is not None
        or state.get("supervisor_pid") != args.expected_supervisor
        or deadline <= parse_deadline(state["expires_at"])
    ):
        parser.error("The legacy running session or extension does not match the request.")
    old, services = open_services(state)
    supervise(run, state, deadline, old, services)


if __name__ == "__main__":
    main()
