# TenderGuard Africa Docker Installation

This guide runs TenderGuard Africa as a downloadable, self-hosted AI agent on Windows
or Linux. The deployment uses free and open-source components and requires no paid AI
API. The API evaluates evidence only: it cannot award, reject, disqualify, or select a
bidder. Every successful autonomous run stops at `AWAITING_HUMAN_REVIEW`.

## 1. What Docker runs

The default Compose project starts one TenderGuard container containing:

- Python 3.12 and the FastAPI interface;
- the existing LangGraph procurement workflow;
- the TenderGuard Procurement MCP server, started locally over stdio;
- Node.js 24 and the pinned borrowed Filesystem MCP server, also over stdio;
- read-only synthetic procurement data.

The API is published only on `127.0.0.1:8000`. Reports and audit records use the
`tenderguard_reports` named volume. The application runs as an unprivileged user with
a read-only root filesystem, no Linux capabilities, and no-new-privileges enabled.

Ollama can run on the host (Option A) or in an optional container (Option B). In both
cases the default model is `qwen3:1.7b`. TenderGuard never downloads the model during
application startup.

## 2. Install Docker

### Windows 10 or 11

Open PowerShell as your normal user and install Docker Desktop:

```powershell
winget install --exact --id Docker.DockerDesktop
```

Restart Windows if the installer requests it. Start Docker Desktop and wait until it
reports that the engine is running. Docker Desktop may ask you to enable WSL 2; accept
that supported configuration. Verify the installation:

```powershell
docker version
docker compose version
```

If `winget` is unavailable, download Docker Desktop from
<https://docs.docker.com/desktop/setup/install/windows-install/>.

### Linux

Install Docker Engine and the Compose plugin using the instructions for your
distribution at <https://docs.docker.com/engine/install/>. For Ubuntu, use Docker's
official Ubuntu repository instructions rather than an unofficial package mirror.

Verify both commands after installation:

```bash
docker version
docker compose version
```

If Docker requires `sudo`, either keep using `sudo docker ...` or follow Docker's
documented post-install procedure. Membership in the `docker` group is effectively
root-level access; grant it only to trusted local users.

## 3. Download TenderGuard Africa

If the repository is not already present, use Git:

```powershell
git clone https://github.com/prettyglory/TenderGuard-Africa.git
Set-Location .\TenderGuard-Africa
git switch nairobi-demo-prep
```

All remaining commands in this guide run from the repository root.

## 4. Prepare `.env` and generate the API key

Never put a real API key in `.env.example` or commit `.env`. The Docker build context
explicitly excludes environment files.

In Windows PowerShell:

```powershell
Copy-Item .env.example .env
$apiKey = [guid]::NewGuid().ToString("N")
(Get-Content .env) -replace '^TENDERGUARD_API_KEY=.*$', "TENDERGUARD_API_KEY=$apiKey" | Set-Content .env
Write-Host "Keep this local API key private: $apiKey"
```

In Linux:

```bash
cp .env.example .env
api_key="$(openssl rand -hex 32)"
sed -i "s/^TENDERGUARD_API_KEY=.*/TENDERGUARD_API_KEY=${api_key}/" .env
printf 'Keep this local API key private: %s\n' "$api_key"
```

TenderGuard refuses to evaluate when the configured key is shorter than 32 characters.
The health endpoint intentionally remains unauthenticated so Docker can perform a
local liveness check.

Do not change `TENDERGUARD_BIND_ADDRESS=127.0.0.1` unless a later, hardened deployment
adds TLS, real user authentication, authorization, firewall rules, and secure audit
storage. A shared API key is not production identity management.

## 5. Choose an Ollama configuration

### Option A: Ollama on the host

This is the default in `.env`:

```text
TENDERGUARD_OLLAMA_URL=http://host.docker.internal:11434/api/chat
TENDERGUARD_OLLAMA_MODEL=qwen3:1.7b
```

Install Ollama on Windows with:

```powershell
winget install --exact --id Ollama.Ollama
```

Or use the official Windows/Linux downloads at <https://ollama.com/download>.

Start Ollama and download the model once:

```powershell
ollama pull qwen3:1.7b
ollama list
```

Docker Desktop normally routes `host.docker.internal` to the Windows host. Keep
Ollama's default local binding first. If the container cannot reach host Ollama, using
Option B is safer than broadly exposing port 11434.

On Linux, Compose maps `host.docker.internal` to the host gateway. Ollama must listen
on an address reachable from that Docker bridge, not only `127.0.0.1`. Configure
`OLLAMA_HOST` for the Docker bridge address and restrict port 11434 with the host
firewall. Do not publish or router-forward that port. Because bridge addresses and
firewall tools vary by distribution, Option B is the recommended Linux setup when a
bridge-only host binding cannot be configured confidently.

Never bind Ollama to an untrusted public interface without authentication and network
controls. TenderGuard does not require public Ollama access.

### Option B: Ollama in Docker

Change the Ollama URL in `.env`:

```powershell
(Get-Content .env) -replace '^TENDERGUARD_OLLAMA_URL=.*$', 'TENDERGUARD_OLLAMA_URL=http://ollama:11434/api/chat' | Set-Content .env
```

Linux equivalent:

```bash
sed -i 's#^TENDERGUARD_OLLAMA_URL=.*#TENDERGUARD_OLLAMA_URL=http://ollama:11434/api/chat#' .env
```

Start only Ollama, pull the model once into its named volume, then start both services:

```powershell
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull qwen3:1.7b
docker compose --profile ollama up -d
```

The `ollama_models` volume keeps the model across container replacement and ordinary
`docker compose down` operations. The Ollama service has no published host port; only
containers on the Compose network can reach it.

To use another locally available model, change `TENDERGUARD_OLLAMA_MODEL` and pull that
exact model yourself. Test its structured-output behavior before relying on it.

## 6. Build and start TenderGuard

For host Ollama:

```powershell
docker compose build
docker compose up -d
docker compose ps
```

For Dockerized Ollama, keep including the profile:

```powershell
docker compose build
docker compose --profile ollama up -d
docker compose ps
```

Follow application logs when diagnosing startup:

```powershell
docker compose logs -f tenderguard
```

Press `Ctrl+C` to stop following logs; the container continues running.

## 7. Check API health

In PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Expected response:

```text
status service
------ -------
ok     tenderguard-africa
```

The health endpoint proves that FastAPI is alive. It intentionally does not download a
model or run a procurement evaluation.

## 8. Run the synthetic evaluation

Read the API key back from `.env`, send the demo request, and inspect the result:

```powershell
$apiKey = ((Get-Content .env | Where-Object { $_ -like 'TENDERGUARD_API_KEY=*' }) -split '=', 2)[1]
$headers = @{ 'X-TenderGuard-Key' = $apiKey }
$body = @{
    tender_id = 'TG-DEMO-001'
    bid_id = 'BID-BETA-001'
} | ConvertTo-Json
$result = Invoke-RestMethod `
    -Uri http://127.0.0.1:8000/api/evaluations `
    -Method Post `
    -ContentType 'application/json' `
    -Headers $headers `
    -Body $body
$result | ConvertTo-Json -Depth 10
```

The expected workflow status is:

```text
AWAITING_HUMAN_REVIEW
```

`final_award_decision` must be `null`. The Beta bid should have review priority
`ATTENTION_REQUIRED`. This is decision support, not bidder rejection or award.

## 9. Find audit records and reports

Every Procurement MCP tool call appends to the persistent audit log:

```powershell
docker compose exec tenderguard ls -la /app/reports
docker compose exec tenderguard tail -n 5 /app/reports/audit_log.jsonl
```

The evaluation API deliberately exposes no approval or report-generation endpoint. For
the local synthetic demonstration only, a named person who has actually reviewed the
findings can run the existing CLI gate:

```powershell
docker compose exec tenderguard python -m app.agent.approve `
    --tender TG-DEMO-001 `
    --bid BID-BETA-001 `
    --approved-by 'Demo Procurement Reviewer'
```

The resulting Markdown document is marked `DRAFT_FOR_COMMITTEE_REVIEW`. Copy a file
from the volume to the local ignored `reports` folder when needed:

```powershell
docker compose cp tenderguard:/app/reports/BID-BETA-001_evaluation_report.md .\reports\BID-BETA-001_evaluation_report.md
```

Supplying an approver name is an audit field and a prototype gate, not verified human
identity or production authorization. A production version requires authenticated
reviewer accounts, roles, separation of duties, and tamper-evident audit controls.

## 10. Stop, restart, and preserve data

Stop and remove the containers and network while retaining named volumes:

```powershell
docker compose down
```

Start them again:

```powershell
docker compose up -d
```

Or, for Dockerized Ollama:

```powershell
docker compose --profile ollama up -d
```

Confirm that audit files survived:

```powershell
docker compose exec tenderguard ls -la /app/reports
```

`docker compose down` does **not** delete the `tenderguard_reports` or `ollama_models`
volumes. The following command permanently deletes both volumes and all reports,
audit records, and downloaded model data they contain:

```powershell
docker compose down --volumes
```

Use `--volumes` only after exporting anything that must be retained. This deletion is
not recoverable through Docker Compose.

## 11. Troubleshooting

### Docker says the API key is required

Confirm `.env` exists and the key line is at least 32 characters:

```powershell
Select-String '^TENDERGUARD_API_KEY=.{32,}$' .env
```

Do not paste the key into issue reports or screenshots.

### Health returns connection refused

Check status and logs:

```powershell
docker compose ps
docker compose logs tenderguard
```

Also check whether another process already owns port 8000. To use another local port,
set `TENDERGUARD_PORT=8080` in `.env` and call `http://127.0.0.1:8080`.

### Evaluation returns 401

The `X-TenderGuard-Key` header is missing or does not exactly match `.env`. Read the key
again in the current terminal and retry. Do not disable authentication.

### Evaluation reports Ollama unavailable

For host Ollama:

```powershell
ollama list
ollama run qwen3:1.7b 'Reply with OK'
```

Confirm `.env` uses `http://host.docker.internal:11434/api/chat`. On Linux, review the
bridge binding and firewall notes in Option A.

For Dockerized Ollama:

```powershell
docker compose --profile ollama ps
docker compose logs ollama
docker compose exec ollama ollama list
```

Confirm `.env` uses `http://ollama:11434/api/chat`. Pull the model if it is absent.

### Filesystem MCP fails to start

Check that the image was rebuilt after an update:

```powershell
docker compose build --no-cache tenderguard
docker compose up -d tenderguard
docker compose logs tenderguard
```

The image contains the pinned Filesystem MCP package; it does not use `npx` to download
that server during application startup.

### Reports disappear after restart

Run `docker volume ls` and confirm the Compose project still has its
`tenderguard_reports` volume. Ordinary `down` preserves it; `down --volumes`, manual
volume removal, or changing the Compose project name can make a different empty volume
appear.

## 12. Security and offline limitations

- Keep the API on localhost. The shared key is a local prototype control, not enterprise
  authentication or multi-user authorization.
- The API returns decision-support summaries but does not serve raw supplier files,
  reports, or audit logs.
- Synthetic data is baked into the read-only image. There is no upload endpoint in this
  phase. Identifiers are validated and model prompts label evidence fields as untrusted
  data, but production ingestion still needs schema validation, malware scanning, and
  stronger prompt-injection defenses.
- Named human approval does not verify the person's identity. Production deployments
  need authenticated reviewers and authorization at both API and MCP boundaries.
- Named volumes are not automatically encrypted or backed up. Protect the Docker host,
  restrict local users, and define retention and backup procedures before real data use.
- The first build and model pull require internet access. Fully offline operation is
  possible only after all images, packages, and model weights are present locally and
  the exact offline workflow has been tested.
- Phase 2 does not add public remote MCP, cloud hosting, payment processing, or license
  enforcement. Those remain later-phase work.
