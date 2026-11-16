"""Deployment refusals must precede Docker mutations and private output disclosure."""

from datetime import UTC, datetime

import pytest

from deploy.aws import configure_env, deploy_stack


@pytest.fixture
def private_env(tmp_path):
    target = tmp_path / ".env"
    configure_env.write_configuration(
        target, "demo.tenderguard.test", "operator@test.org", "a-private$literal password-123"
    )
    return target


def test_check_only_never_contacts_imds_or_starts_containers(private_env, monkeypatch, capsys):
    operations = []
    monkeypatch.setattr(deploy_stack, "run_command", lambda args, **_: operations.append(args))
    monkeypatch.setattr(
        deploy_stack, "instance_identity", lambda: pytest.fail("Check-only contacted IMDS")
    )
    deploy_stack.deploy(private_env, None, check_only=True)
    assert len(operations) == 1
    assert operations[0][-2:] == ["config", "--quiet"]
    assert "literal" not in capsys.readouterr().out


@pytest.mark.parametrize("expected", [None, deploy_stack.PROTECTED_INSTANCE])
def test_protected_or_unspecified_host_never_reaches_imds(private_env, monkeypatch, expected):
    operations = []
    monkeypatch.setattr(deploy_stack, "run_command", lambda args, **_: operations.append(args))
    monkeypatch.setattr(
        deploy_stack, "instance_identity", lambda: pytest.fail("Protected host contacted IMDS")
    )
    with pytest.raises(ValueError):
        deploy_stack.deploy(private_env, expected)
    assert all(args[-2:] == ["config", "--quiet"] for args in operations)


@pytest.mark.parametrize(
    "changes",
    [
        {"instanceId": deploy_stack.PROTECTED_INSTANCE},
        {"region": "us-east-1"},
        {"pendingTime": "2026-11-16T00:00:00Z"},
    ],
)
def test_unapproved_identity_or_expired_window_never_reaches_systemd(monkeypatch, changes):
    identity = {
        "instanceId": "i-1234567890abcdef0",
        "region": "eu-north-1",
        "pendingTime": "2026-11-16T12:00:00Z",
        **changes,
    }
    monkeypatch.setattr(
        deploy_stack, "run_command", lambda *_: pytest.fail("Invalid identity reached systemd")
    )
    with pytest.raises(ValueError):
        deploy_stack.validate_host(
            "i-1234567890abcdef0", identity, now=datetime(2026, 11, 16, 14, tzinfo=UTC)
        )


@pytest.mark.parametrize("timer", ["Persistent=true", "OnCalendar=2026-11-16 20:00:00 UTC"])
def test_timer_requires_both_exact_deadline_and_reboot_persistence(monkeypatch, timer):
    monkeypatch.setattr(deploy_stack, "run_command", lambda *_: timer)
    with pytest.raises(ValueError, match="persistent shutdown timer"):
        deploy_stack.validate_host(
            "i-1234567890abcdef0",
            {
                "instanceId": "i-1234567890abcdef0",
                "region": "eu-north-1",
                "pendingTime": "2026-11-16T12:00:00Z",
            },
            now=datetime(2026, 11, 16, 14, tzinfo=UTC),
        )


def test_failed_cutoff_guard_blocks_every_docker_mutation(private_env, monkeypatch):
    operations = []
    monkeypatch.setattr(deploy_stack, "run_command", lambda args, **_: operations.append(args))
    monkeypatch.setattr(deploy_stack, "instance_identity", dict)

    def refused(*_):
        raise ValueError("Inactive shutdown timer")

    monkeypatch.setattr(deploy_stack, "validate_host", refused)
    with pytest.raises(ValueError, match="Inactive"):
        deploy_stack.deploy(private_env, "i-1234567890abcdef0")
    assert len(operations) == 1
    assert operations[0][-2:] == ["config", "--quiet"]


def test_deployment_rechecks_cutoff_and_waits_for_model_service(private_env, monkeypatch):
    operations, guards = [], []
    monkeypatch.setattr(deploy_stack, "run_command", lambda args, **_: operations.append(args))
    monkeypatch.setattr(deploy_stack, "instance_identity", lambda: {"approved": True})
    monkeypatch.setattr(deploy_stack, "validate_host", lambda *args: guards.append(args))
    deploy_stack.deploy(private_env, "i-1234567890abcdef0")
    commands = [args[args.index("-f") + 2 :] for args in operations]
    assert commands == [
        ["config", "--quiet"],
        ["build"],
        ["up", "-d", "--wait", "--wait-timeout", "120", "ollama"],
        ["exec", "-T", "ollama", "ollama", "pull", "qwen3:1.7b"],
        ["up", "-d", "--wait", "--wait-timeout", "180"],
    ]
    assert len(guards) == 5
