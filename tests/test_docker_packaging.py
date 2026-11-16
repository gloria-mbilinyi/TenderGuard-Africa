from pathlib import Path

import yaml

from app.agent.filesystem_mcp import FILESYSTEM_MCP_PACKAGE, _server_parameters

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (PROJECT_ROOT / name).read_text(encoding="utf-8")


def test_dockerfile_uses_pinned_non_root_runtime_and_healthcheck():
    dockerfile = _read("Dockerfile")

    assert "python:${PYTHON_VERSION}-slim-bookworm" in dockerfile
    assert "node:${NODE_VERSION}-bookworm-slim" in dockerfile
    assert '"@modelcontextprotocol/server-filesystem@${FILESYSTEM_MCP_VERSION}"' in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "/api/health" in dockerfile
    assert "npm ci" in dockerfile
    assert "npm run build" in dockerfile
    assert "/src/frontend/dist ./frontend/dist" in dockerfile
    assert "COPY . " not in dockerfile


def test_compose_defaults_to_localhost_and_persistent_reports():
    compose = yaml.safe_load(_read("compose.yaml"))
    service = compose["services"]["tenderguard"]

    assert service["ports"] == [
        "${TENDERGUARD_BIND_ADDRESS:-127.0.0.1}:${TENDERGUARD_PORT:-8000}:8000"
    ]
    assert "tenderguard_reports:/app/reports" in service["volumes"]
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in service["security_opt"]
    assert "TENDERGUARD_DASHBOARD_PASSWORD" in service["environment"]
    assert "tenderguard_reports" in compose["volumes"]


def test_compose_ollama_is_optional_and_does_not_auto_pull_models():
    compose_text = _read("compose.yaml")
    compose = yaml.safe_load(compose_text)
    ollama = compose["services"]["ollama"]

    assert ollama["profiles"] == ["ollama"]
    assert "ollama_models:/root/.ollama" in ollama["volumes"]
    assert "ollama pull" not in compose_text.lower()
    assert "ollama_models" in compose["volumes"]


def test_docker_context_excludes_secrets_and_runtime_records():
    dockerignore = _read(".dockerignore").splitlines()

    assert ".env" in dockerignore
    assert ".env.*" in dockerignore
    assert "reports/*" in dockerignore
    assert ".git" in dockerignore


def test_filesystem_mcp_is_pinned_read_only_and_reports_scoped(monkeypatch):
    monkeypatch.delenv("TENDERGUARD_FILESYSTEM_MCP_COMMAND", raising=False)
    parameters = _server_parameters()
    command_line = [parameters.command, *parameters.args]

    assert FILESYSTEM_MCP_PACKAGE in command_line
    assert "--read-only" in command_line
    assert "--confine-roots" in command_line
    assert command_line[-1].replace("\\", "/").endswith("/reports")


def test_container_can_select_preinstalled_filesystem_mcp(monkeypatch):
    command = "/opt/filesystem-mcp/node_modules/.bin/mcp-server-filesystem"
    monkeypatch.setenv("TENDERGUARD_FILESYSTEM_MCP_COMMAND", command)

    parameters = _server_parameters()

    assert parameters.command == command
    assert "--read-only" in parameters.args
    assert FILESYSTEM_MCP_PACKAGE not in parameters.args
