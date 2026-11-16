"""Probe the actual CI model context and summarize failures without exposing prompts."""

import re

import httpx

from deploy.validation.smoke import compose

MODEL_URL = "http://127.0.0.1:11434"


def warm_model(client: httpx.Client) -> None:
    response = client.post(
        "/api/generate",
        json={
            "model": "qwen3:1.7b",
            "stream": False,
            "think": False,
            "prompt": "Reply READY.",
            "keep_alive": "30m",
            "options": {"num_ctx": 8192, "num_predict": 1, "temperature": 0},
        },
        timeout=120,
    )
    if response.status_code != 200 or response.json().get("done") is not True:
        raise RuntimeError("The configured Qwen model did not complete its readiness probe.")
    print("Qwen readiness probe completed with the production 8192-token context.")


def sanitized_diagnostics(project: str) -> dict:
    # Ollama debug output is never forwarded: logs can include document-derived text.
    captured = compose(project, "logs", "--no-color", "--tail", "400", "ollama", check=False)
    logs = captured.stdout + captured.stderr
    return {
        "ollama_log_read_succeeded": captured.returncode == 0,
        "ollama_http_500_count": len(re.findall(r"\[GIN\].*?\|\s*500\s*\|", logs)),
        "cancelled_request_count": len(
            re.findall(r"context cancel|request cancel", logs, re.IGNORECASE)
        ),
        "truncated_prompt_count": logs.lower().count("truncating input prompt"),
        "runner_error_count": len(re.findall(r"runner.*?(?:error|failed)", logs, re.IGNORECASE)),
    }


def main() -> None:
    with httpx.Client(base_url=MODEL_URL, timeout=120) as client:
        warm_model(client)


if __name__ == "__main__":
    main()
