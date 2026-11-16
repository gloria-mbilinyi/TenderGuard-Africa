# TenderGuard Africa: Phase 1 Local API

This is an **experimental local-only API** on top of the existing TenderGuard LangGraph + MCP workflow. It does not support report approval, customer authentication, billing, or real procurement data. **Do not expose it to the public internet.** The shared API key is suitable only for a local prototype, not commercial deployment.

## Prerequisites

Python 3.12, Ollama, and `qwen3:1.7b` as documented in the main README. No paid API keys or cloud services are necessary.

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
ollama pull qwen3:1.7b
$env:TENDERGUARD_API_KEY = [guid]::NewGuid().ToString("N")
Write-Host "Temporary local API key:" $env:TENDERGUARD_API_KEY
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

In a **second PowerShell terminal** in the same repository, activate the environment and set the **same** local API key used by the server (PowerShell environment variables do not automatically transfer between terminals):

```powershell
.\.venv\Scripts\Activate.ps1
$env:TENDERGUARD_API_KEY = "<paste-the-key-from-the-server-terminal>"
Invoke-RestMethod http://127.0.0.1:8000/api/health
$body = @{ tender_id = "TG-DEMO-001"; bid_id = "BID-BETA-001" } | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/evaluations -Method Post -ContentType "application/json" -Headers @{ "X-TenderGuard-Key" = $env:TENDERGUARD_API_KEY } -Body $body
```

Copy the generated key from the first terminal; keep it private. You may also test the health endpoint in a browser at `http://127.0.0.1:8000/api/health`.

### Configurable local AI

Default model: `qwen3:1.7b` served on `http://localhost:11434/api/chat`. To change either value **before starting** the API server:

```powershell
$env:TENDERGUARD_OLLAMA_URL = "http://localhost:11434/api/chat"
$env:TENDERGUARD_OLLAMA_MODEL = "qwen3:1.7b"
```

This is groundwork for Docker networking, not a cloud deployment.

### Run API unit tests

```powershell
python -m pytest -q tests/test_api.py
```

The tests mock the existing agent and do not call a paid API, download a model, or process real documents.

### Security boundaries and next steps

- The evaluation API is read-only with respect to procurement decisions. It **does not expose report generation or human approval**.
- Every successful evaluation ends at `AWAITING_HUMAN_REVIEW` and has a null award decision.
- The endpoint currently waits for the evaluation to finish; a background queue is needed before handling concurrent production users.
- A shared local API key **is not** enterprise identity, multi-tenant authorization, or remote MCP authentication.
- `/api/health` is a basic liveness response and does not test Ollama or database availability.
- Synthetic bids only. Validate input, evidence quality and scanned-PDF extraction before any real use.
- Production work must include authentic reviewer identities, per-organization isolation, encrypted storage, hardened audit logging, and permissions at the MCP tool layer.
