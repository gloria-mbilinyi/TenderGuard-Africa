"""Cloud preparation checks that require no AWS credentials or billable resources."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import yaml
from dotenv import dotenv_values

from deploy.aws import configure_env, preflight, verify_cloud
from deploy.aws.shutdown_deadline import shutdown_deadline


def test_shutdown_is_eight_hours_from_launch_not_from_later_installation():
    identity = {"instanceId": "i-demo", "pendingTime": "2026-11-16T12:00:00Z"}
    later_install_time = datetime(2026, 11, 16, 14, 0, tzinfo=UTC)
    assert shutdown_deadline(identity, "i-demo", now=later_install_time) == datetime(
        2026, 11, 16, 20, 0, tzinfo=UTC
    )


@pytest.mark.parametrize(
    "change",
    [
        {"instanceId": "i-unrelated"},
        {"pendingTime": "2026-11-16T12:00:00"},
        {"pendingTime": "2026-11-17T12:00:00Z"},
    ],
)
def test_shutdown_rejects_wrong_instance_and_unreliable_launch_time(change):
    identity = {"instanceId": "i-demo", "pendingTime": "2026-11-16T12:00:00Z", **change}
    with pytest.raises(ValueError):
        shutdown_deadline(identity, "i-demo", now=datetime(2026, 11, 16, 14, 0, tzinfo=UTC))


@pytest.mark.parametrize(
    "domain",
    [
        "http://example.org",
        "127.0.0.1",
        "localhost",
        "tenderguard.example.org",
        "host.invalid/path",
        "host.invalid:443",
        "host..invalid",
        "-host.invalid",
    ],
)
def test_cloud_secret_setup_rejects_insecure_or_placeholder_domains(domain):
    with pytest.raises(ValueError):
        configure_env.validate_domain(domain)


def test_cloud_secrets_are_private_literal_and_never_overwritten(tmp_path, capsys):
    target = tmp_path / ".env"
    password = "A-strong$literal-password-123"
    configure_env.write_configuration(
        target, "demo.tenderguard.test", "operator@test.org", password
    )
    values = dotenv_values(target, interpolate=False)
    assert values["TENDERGUARD_DASHBOARD_PASSWORD"] == password
    assert len(values["TENDERGUARD_API_KEY"]) >= 32
    assert capsys.readouterr().out == ""
    original = target.read_bytes()
    with pytest.raises(FileExistsError):
        configure_env.write_configuration(target, "other.tenderguard.test", "x@test.org", password)
    assert target.read_bytes() == original


@pytest.mark.parametrize(
    "password",
    [
        "too-short",
        "password\nwith-newline-123",
        "a'quoted-password-123",
        "trailing-backslash-123\\",
    ],
)
def test_invalid_password_never_writes_environment(tmp_path, password):
    target = tmp_path / ".env"
    with pytest.raises(ValueError):
        configure_env.write_configuration(
            target, "demo.tenderguard.test", "operator@test.org", password
        )
    assert not target.exists()


def test_preflight_stops_without_cli_and_never_implies_cost_approval(monkeypatch):
    monkeypatch.setattr(preflight.shutil, "which", lambda _: None)
    report = preflight.inspect_account()
    assert report["identity"] == {"error": "AWS_CLI_UNAVAILABLE"}
    assert report["region"] == "eu-north-1"
    assert report["credit_coverage_verified"] is False
    assert report["launch_authorized"] is False
    assert "existing_instances" not in report


def test_price_extraction_uses_only_unambiguous_on_demand_hourly_rates():
    def product(rate):
        return json.dumps(
            {
                "terms": {
                    "OnDemand": {
                        "term": {
                            "priceDimensions": {
                                "dimension": {"unit": "Hrs", "pricePerUnit": {"USD": rate}}
                            }
                        }
                    }
                }
            }
        )

    assert preflight.hourly_rate({"PriceList": [product("0.081")]}) == Decimal("0.081")
    assert preflight.hourly_rate({"PriceList": [product("0.081"), product("0.099")]}) is None
    assert preflight.hourly_rate({"error": "AccessDenied"}) is None


def test_cloud_compose_limits_model_parallelism_logs_and_public_ports():
    root = Path(__file__).resolve().parents[1]
    compose = yaml.safe_load((root / "deploy/aws/compose.aws.yaml").read_text(encoding="utf-8"))
    for service in compose["services"].values():
        assert service["logging"]["driver"] == "local"
        assert service["logging"]["options"] == {"max-size": "10m", "max-file": "3"}
    assert "ports" not in compose["services"]["ollama"]
    assert "ports" not in compose["services"]["tenderguard"]
    environment = compose["services"]["ollama"]["environment"]
    assert environment["OLLAMA_NUM_PARALLEL"] == "1"
    assert environment["OLLAMA_MAX_LOADED_MODELS"] == "1"


@pytest.mark.parametrize(
    "origin", ["http://demo.test", "https://user:pass@demo.test", "https://demo.test/path"]
)
def test_cloud_verifier_never_sends_password_to_http_or_credential_urls(origin):
    with pytest.raises(ValueError):
        verify_cloud.https_origin(origin)


def test_cloud_verifier_rejects_missing_secure_cookie_flags():
    def respond(request):
        if request.url.path == "/api/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/api/browser/reports":
            return httpx.Response(401)
        password = json.loads(request.content)["password"]
        if password != "private-password":
            return httpx.Response(401)
        return httpx.Response(
            200,
            json={"csrf_token": "csrf"},
            headers={
                "set-cookie": "tenderguard_session=test; HttpOnly; SameSite=Strict",
            },
        )

    with (
        httpx.Client(
            base_url="https://demo.test", transport=httpx.MockTransport(respond)
        ) as client,
        pytest.raises(RuntimeError, match="secure session cookie"),
    ):
        verify_cloud.verify_login(client, "https://demo.test", "private-password")
