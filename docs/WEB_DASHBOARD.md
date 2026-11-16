# TenderGuard Africa Web Dashboard

The Phase 3 dashboard is a real React and TypeScript interface for the existing
TenderGuard evaluation workflow. It does not simulate analysis in the browser.
Submitting an evaluation calls FastAPI, which invokes the same LangGraph graph,
Procurement MCP tools, and local Ollama model used by the CLI.

The dashboard is decision support only. Every successful autonomous evaluation ends
at `AWAITING_HUMAN_REVIEW`, with `human_committee_required = true` and
`final_award_decision = null`.

## Prerequisites

- Python 3.12 with the project installed in `.venv`
- Node.js 20 or newer and npm
- Ollama running locally
- `qwen3:1.7b` installed with `ollama pull qwen3:1.7b`

## Local development

From the repository root, set private local credentials in the current PowerShell
session. Do not place either value in frontend environment variables.

```powershell
$env:TENDERGUARD_API_KEY = [guid]::NewGuid().ToString("N")
$env:TENDERGUARD_DASHBOARD_PASSWORD = "replace-with-a-private-password"
$env:TENDERGUARD_OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
$env:TENDERGUARD_OLLAMA_MODEL = "qwen3:1.7b"
```

Start FastAPI in one terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Start Vite in a second terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` and sign in with the dashboard password. Vite proxies
`/api` requests to FastAPI without putting a backend API key in the browser.

## Production-style local build

Build the static UI before starting FastAPI:

```powershell
Set-Location frontend
npm ci
npm run build
Set-Location ..
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

FastAPI serves `frontend/dist` at `http://127.0.0.1:8000`. Build before importing or
starting the API process so the static mount is present.

## Docker

The multi-stage Dockerfile builds the frontend and copies only `frontend/dist` into
the unprivileged runtime image. Configure `.env` before starting Compose:

```powershell
Copy-Item .env.example .env
$apiKey = [guid]::NewGuid().ToString("N")
(Get-Content .env) -replace '^TENDERGUARD_API_KEY=.*$', "TENDERGUARD_API_KEY=$apiKey" |
  Set-Content .env
(Get-Content .env) -replace '^TENDERGUARD_DASHBOARD_PASSWORD=.*$',
  'TENDERGUARD_DASHBOARD_PASSWORD=replace-with-a-private-password' | Set-Content .env
docker compose build
docker compose up -d
```

Then open `http://127.0.0.1:8000`. Keep the default localhost binding unless a
proper HTTPS reverse proxy and production identity layer have been added.

## Authentication boundary

The browser and programmatic clients use separate mechanisms:

- The browser signs in with `TENDERGUARD_DASHBOARD_PASSWORD`. FastAPI stores an
  opaque server-side session and sends its identifier only in an `HttpOnly`,
  `SameSite=Strict` cookie scoped to `/api/browser`.
- State-changing browser requests require an origin check and an in-memory CSRF
  token. The frontend never stores the password, session identifier, CSRF token, or
  API key in local storage.
- Programmatic `POST /api/evaluations` clients continue to use
  `X-TenderGuard-Key` with `TENDERGUARD_API_KEY`.

This password gate is intentionally described as a local single-operator demo
control. Sessions are in memory and are invalidated by an API restart. It is not
production identity, multi-user access control, or institutional RBAC.

## Browser capabilities

The authenticated dashboard can:

- read the synthetic tender and bid catalog;
- run a real evaluation;
- display validated compliance, price, supplier-risk, and source evidence;
- show completed evaluations from the current server process;
- list and download legitimately generated draft Markdown reports;
- display sanitized API and Ollama status.

The dashboard cannot:

- award, reject, disqualify, or select a bidder;
- approve or generate a report;
- read audit logs or arbitrary files;
- access backend credentials;
- bypass the catalog, Pydantic validation, or human-review state.

Report authorization stays in the separate local CLI because the current
`approved_by` string does not verify a person's identity. Browser approval should be
added only with authenticated roles and an auditable institutional identity system.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
Set-Location frontend
npm test
npm run build
```

The tests cover session cookies, origin and CSRF enforcement, catalog selection,
structured evidence, report-library isolation, frontend credential handling, and the
mandatory null award decision.
