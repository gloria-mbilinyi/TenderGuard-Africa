"""Extending a live demo must preserve its services until the acknowledged cutoff."""

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta

import pytest

from deploy import temporary_demo as demo
from deploy import temporary_demo_watchdog as watchdog

NOW = datetime(2026, 11, 17, 0, tzinfo=UTC)
DEADLINE = datetime(2026, 11, 17, 17, 47, tzinfo=UTC)


def test_extension_uses_explicit_nairobi_offset():
    assert demo.requested_deadline("2026-11-17T20:47:00+03:00", now=NOW) == DEADLINE


@pytest.mark.parametrize(
    "value", ["2026-11-17T20:47:00", "2026-11-16T20:47:00Z", "2026-11-19T20:47:00Z"]
)
def test_extension_rejects_ambiguous_past_or_unbounded_time(value):
    with pytest.raises(ValueError):
        demo.requested_deadline(value, now=NOW)


def test_control_file_can_extend_but_not_shorten_or_cross_runs(tmp_path):
    fallback = NOW + timedelta(hours=8)
    for value in ["malformed", json.dumps({"run_id": "other", "expires_at": DEADLINE.isoformat()})]:
        (tmp_path / "deadline.json").write_text(value)
        assert demo.read_deadline(tmp_path, fallback) == fallback
    for deadline, expected in [(NOW, fallback), (DEADLINE, DEADLINE)]:
        demo.write_json(
            tmp_path / "deadline.json",
            {"run_id": tmp_path.name, "expires_at": deadline.isoformat()},
        )
        assert demo.read_deadline(tmp_path, fallback) == expected


def test_extension_requires_live_acknowledgment_and_preserves_private_files(tmp_path, monkeypatch):
    state = {
        "status": "RUNNING",
        "control_version": 1,
        "expires_at": (NOW + timedelta(hours=8)).isoformat(),
    }
    demo.write_json(tmp_path / "status.json", state)
    password = tmp_path / "dashboard-password.txt"
    password.write_text("unchanged-private-password")
    monkeypatch.setattr(demo, "current_run", lambda: tmp_path)
    monkeypatch.setattr(demo, "requested_deadline", lambda _: DEADLINE)

    def acknowledge(_):
        control = json.loads((tmp_path / "deadline.json").read_text())
        demo.write_json(tmp_path / "status.json", {**state, "expires_at": control["expires_at"]})

    monkeypatch.setattr(demo.time, "sleep", acknowledge)
    demo.extend_until("2026-11-17T20:47:00+03:00")
    assert password.read_text() == "unchanged-private-password"
    assert json.loads((tmp_path / "status.json").read_text())["expires_at"] == DEADLINE.isoformat()


def test_legacy_deadline_file_alone_cannot_claim_extension(tmp_path, monkeypatch):
    demo.write_json(tmp_path / "status.json", {"status": "RUNNING", "expires_at": NOW.isoformat()})
    monkeypatch.setattr(demo, "current_run", lambda: tmp_path)
    monkeypatch.setattr(demo, "requested_deadline", lambda _: DEADLINE)
    with pytest.raises(RuntimeError, match="takeover"):
        demo.extend_until(DEADLINE.isoformat())
    assert not (tmp_path / "deadline.json").exists()


def test_watchdog_transfer_keeps_services_alive_past_old_cutoff(tmp_path, monkeypatch):
    now = [NOW]
    events = []

    class Clock:
        @staticmethod
        def now(_):
            return now[0]

    class Process:
        def __init__(self, pid):
            self.pid = pid
            self.running = True

        def alive(self):
            return self.running

        def terminate(self):
            events.append(("terminated", self.pid, now[0]))
            self.running = False

        def close(self):
            events.append(("closed", self.pid, now[0]))

    old, tunnel, backend = Process(1), Process(2), Process(3)
    state = {"status": "RUNNING", "expires_at": (NOW + timedelta(hours=8)).isoformat()}

    def advance(_):
        assert not old.running and tunnel.running and backend.running
        acknowledged = json.loads((tmp_path / "status.json").read_text())
        assert acknowledged["expires_at"] == DEADLINE.isoformat()
        now[0] = NOW + timedelta(hours=8) if now[0] == NOW else DEADLINE

    monkeypatch.setattr(watchdog, "datetime", Clock)
    monkeypatch.setattr(watchdog.time, "sleep", advance)
    watchdog.supervise(tmp_path, state, DEADLINE, old, [tunnel, backend])
    assert events[0] == ("terminated", 1, NOW)
    assert all(
        event[2] == DEADLINE for event in events if event[0] == "terminated" and event[1] != 1
    )
    assert json.loads((tmp_path / "status.json").read_text())["status"] == "STOPPED"


def test_controller_error_does_not_terminate_the_active_demo(tmp_path, monkeypatch):
    class Process:
        pid = 123
        terminated = False

        def alive(self):
            return True

        def terminate(self):
            self.terminated = True

        def close(self):
            pass

    old, server = Process(), Process()
    real_write = watchdog.write_json

    def fail_status(path, state):
        if path.name == "status.json":
            raise OSError("Simulated disk failure")
        real_write(path, state)

    monkeypatch.setattr(watchdog, "write_json", fail_status)
    with pytest.raises(OSError):
        watchdog.supervise(tmp_path, {}, DEADLINE, old, [server])
    assert old.terminated and not server.terminated


@pytest.mark.skipif(os.name != "nt", reason="Windows process takeover integration")
def test_windows_terminating_watchdog_leaves_its_child_running(tmp_path):
    child_file = tmp_path / "child-pid.txt"
    code = (
        "import subprocess,sys,time; from pathlib import Path; "
        "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'],creationflags=0x08000000); "
        "Path(sys.argv[1]).write_text(str(child.pid)); time.sleep(60)"
    )
    parent = subprocess.Popen(
        [sys._base_executable, "-c", code, str(child_file)],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    handles = []
    try:
        for _ in range(100):
            if child_file.exists():
                break
            time.sleep(0.05)
        child_pid = int(child_file.read_text())
        old = watchdog.WindowsProcess(parent.pid, sys._base_executable)
        child = watchdog.WindowsProcess(child_pid, sys._base_executable)
        handles.extend([old, child])
        with pytest.raises(ValueError, match="reused"):
            watchdog.WindowsProcess(parent.pid, sys._base_executable, "2000-01-01T00:00:00Z")
        old.terminate()
        assert child.alive()
        child.terminate()
        assert not child.alive()
    finally:
        for handle in reversed(handles):
            handle.terminate()
            handle.close()
        if parent.poll() is None:
            parent.kill()
        parent.wait(timeout=10)
