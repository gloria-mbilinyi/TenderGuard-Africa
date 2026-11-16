"""Readiness must exercise real model generation and diagnostics must redact content."""

import json
import subprocess

import httpx
import pytest

from deploy.validation import model_readiness


def test_readiness_checks_production_model_context_and_completion(capsys):
    def respond(request):
        payload = json.loads(request.content)
        assert payload["model"] == "qwen3:1.7b"
        assert payload["options"] == {"num_ctx": 8192, "num_predict": 1, "temperature": 0}
        assert payload["stream"] is False and payload["think"] is False
        return httpx.Response(200, json={"done": True, "response": "private test output"})

    with httpx.Client(
        base_url="http://localhost", transport=httpx.MockTransport(respond)
    ) as client:
        model_readiness.warm_model(client)
    assert "private test output" not in capsys.readouterr().out


@pytest.mark.parametrize("status,body", [(503, {}), (200, {"done": False})])
def test_readiness_refuses_unavailable_or_incomplete_model(status, body):
    with (
        httpx.Client(
            base_url="http://localhost",
            transport=httpx.MockTransport(lambda _: httpx.Response(status, json=body)),
        ) as client,
        pytest.raises(RuntimeError, match="readiness"),
    ):
        model_readiness.warm_model(client)


def test_failure_diagnostics_return_counts_and_never_raw_logs(monkeypatch):
    log = (
        "private document text and secret-token\n"
        "[GIN] 2026/11/17 | 500 | 2m0s | private-peer | POST /api/chat\n"
        "context canceled\ntruncating input prompt\nrunner failed\n"
    )
    monkeypatch.setattr(
        model_readiness, "compose", lambda *_, **__: subprocess.CompletedProcess([], 0, log, "")
    )
    result = model_readiness.sanitized_diagnostics("tg-verify-123456abcdef")
    assert result == {
        "ollama_log_read_succeeded": True,
        "ollama_http_500_count": 1,
        "cancelled_request_count": 1,
        "truncated_prompt_count": 1,
        "runner_error_count": 1,
    }
    assert "private" not in json.dumps(result) and "secret-token" not in json.dumps(result)
