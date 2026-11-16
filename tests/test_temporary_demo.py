"""Temporary HTTPS processes must stay inside their own time and storage boundaries."""

import json
import os
import stat
import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from deploy import temporary_demo


def test_credential_directory_is_private_and_does_not_print_identity(tmp_path, capsys):
    private = tmp_path / "private"
    temporary_demo.private_directory(private)
    if os.name == "nt":
        acl = subprocess.run(
            ["icacls", str(private)], capture_output=True, text=True, check=True
        ).stdout
        # A mandatory integrity label can inherit without granting file access.
        assert "(I)(OI)(CI)(F)" not in acl
        assert acl.count("(OI)(CI)(F)") == 2
    else:
        assert stat.S_IMODE(private.stat().st_mode) == 0o700
    assert capsys.readouterr().out == ""


def test_temporary_demo_stop_cannot_escape_runtime_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(temporary_demo, "RUNTIME", tmp_path)
    (tmp_path / "latest.json").write_text('{"run_id": "../other-demo"}')
    with pytest.raises(ValueError, match="boundary"):
        temporary_demo.current_run()


@pytest.mark.parametrize("hours", [-1, 0, 8.1, float("nan")])
def test_temporary_demo_cannot_extend_eight_hour_limit(tmp_path, hours):
    with pytest.raises(ValueError, match="eight hours"):
        temporary_demo.serve(tmp_path / "missing.exe", 8768, hours)


def test_temporary_demo_stops_only_supervised_child():
    class Child:
        def __init__(self):
            self.terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout):
            assert timeout == 10

    child = Child()
    temporary_demo.stop_process(child)
    assert child.terminated


def test_expiry_cleans_up_tunnel_and_server_without_disclosing_credentials(
    tmp_path, monkeypatch, capsys
):
    frontend = tmp_path / "frontend/dist"
    frontend.mkdir(parents=True)
    (frontend / "index.html").touch()
    binary = tmp_path / "cloudflared.exe"
    binary.touch()
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(temporary_demo, "ROOT", tmp_path)
    monkeypatch.setattr(temporary_demo, "RUNTIME", runtime)
    monkeypatch.setattr(temporary_demo, "private_directory", lambda path: path.mkdir())
    started = datetime(2026, 11, 17, 0, tzinfo=UTC)
    times = iter([started, started + timedelta(hours=8)])

    class Clock:
        @staticmethod
        def now(_):
            return next(times)

    class Socket:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def bind(self, address):
            assert address == ("127.0.0.1", 8768)

    class Healthy:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    children = []

    class Child:
        def __init__(self, arguments, **options):
            self.arguments = arguments
            self.options = options
            self.terminated = False
            children.append(self)
            if arguments[0] == str(binary.resolve()):
                options["stdout"].write("https://synthetic-rehearsal.trycloudflare.com")
                options["stdout"].flush()

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout):
            pass

    monkeypatch.setattr(temporary_demo, "datetime", Clock)
    monkeypatch.setattr(temporary_demo.socket, "socket", Socket)
    monkeypatch.setattr(temporary_demo.subprocess, "Popen", Child)
    monkeypatch.setattr(temporary_demo, "urlopen", lambda *_args, **_kwargs: Healthy())
    temporary_demo.serve(binary, 8768, 8)
    assert len(children) == 2 and all(child.terminated for child in children)
    run = temporary_demo.current_run()
    state = json.loads((run / "status.json").read_text())
    assert state["status"] == "STOPPED"
    assert datetime.fromisoformat(state["expires_at"]) == started + timedelta(hours=8)
    environment = children[1].options["env"]
    assert environment["TENDERGUARD_ALLOWED_ORIGINS"] == state["url"]
    assert environment["TENDERGUARD_COOKIE_SECURE"] == "true"
    assert environment["TENDERGUARD_DOCUMENT_STORAGE"] == str(run / "document_evaluations")
    assert "127.0.0.1" in children[1].arguments
    output = capsys.readouterr().out
    for key in ("TENDERGUARD_API_KEY", "TENDERGUARD_DASHBOARD_PASSWORD"):
        assert environment[key] not in output
        assert environment[key] not in (run / "status.json").read_text()
