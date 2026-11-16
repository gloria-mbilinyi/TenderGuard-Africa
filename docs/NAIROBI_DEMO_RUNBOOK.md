# Nairobi demonstration runbook

This runbook drives the real local TenderGuard workflow. It does not use prerecorded
responses or hardcoded findings. Keep the laptop deployment ready even if an approved
AWS deployment is available.

## 1. One-day preflight

- Connect the laptop to power and disable sleep for the presentation window.
- Confirm at least 8 GB free disk space and a reliable local browser.
- Keep `demo_documents/` unchanged and visibly labeled synthetic.
- Confirm Docker/AWS are optional fallbacks, not dependencies for the laptop demo.
- Rehearse once without internet after the Ollama model and dependencies are present.
- Do not use real procurement files, real supplier data, or institutional credentials.

Run verification from the repository root:

```powershell
git status --short
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix frontend run test
npm --prefix frontend run build
ollama list
```

## 2. Secure local startup

Create the virtual environment and install dependencies if this laptop has not already
been prepared:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
npm --prefix frontend ci
npm --prefix frontend run build
ollama pull qwen3:1.7b
```

In the presentation PowerShell window, generate the programmatic API key and enter a
private dashboard password without displaying it:

```powershell
$env:TENDERGUARD_API_KEY = [guid]::NewGuid().ToString('N')
$secret = Read-Host 'Dashboard password (12+ characters)' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
  $env:TENDERGUARD_DASHBOARD_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
  Remove-Variable pointer,secret
}
$env:TENDERGUARD_OLLAMA_URL = 'http://127.0.0.1:11434/api/chat'
$env:TENDERGUARD_OLLAMA_MODEL = 'qwen3:1.7b'
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. The production React build is served by FastAPI. Keep
this PowerShell window running and private; its process environment contains the
session password.

## 3. Live demonstration sequence

1. Show the login page and sign in with the password entered at startup.
2. Open **PDF workspaces** and create `Nairobi synthetic supplier comparison`.
3. Upload `demo_documents/tender_requirements_synthetic.pdf` as the tender.
4. Upload `demo_documents/alpha_supplier_bid_synthetic.pdf` as a supplier bid.
5. Upload `demo_documents/beta_supplier_bid_synthetic.pdf` as a supplier bid.
6. Show the extracted previews and the ready status: one tender and two bids.
7. Select **Evaluate supplier PDFs**. Explain that the spinner represents the real
   Qwen planning, MCP checks, LangGraph workflow, and synthesis; no fake percentage is
   shown because intermediate stages are not streamed.
8. Show the Alpha/Beta comparison, mandatory checks, technical findings, direct price
   context, Beta's missing tax-clearance evidence, risk flag, and page citations.
9. Point out `AWAITING_HUMAN_REVIEW`, `human_committee_required = true`, and the absence
   of any award decision.
10. Copy the workspace ID. In a separate PowerShell with the same repository and
    document-storage environment, run the authorization command below only after a
    named reviewer has reviewed the result:

```powershell
.\.venv\Scripts\python.exe -m app.agent.approve_documents `
  --workspace EVL-REPLACE_WITH_WORKSPACE_ID `
  --approved-by 'Named Demo Reviewer'
```

11. Refresh **Reports**, show `DRAFT_FOR_COMMITTEE_REVIEW`, and download it. State that
    the name is an auditable demo authorization field, not verified reviewer identity.

## 4. Fast fallback paths

If the browser fails, run the same real workflow from the CLI:

```powershell
.\.venv\Scripts\python.exe -m app.agent.run_documents `
  --tender demo_documents\tender_requirements_synthetic.pdf `
  --bid demo_documents\alpha_supplier_bid_synthetic.pdf `
  --bid demo_documents\beta_supplier_bid_synthetic.pdf
```

If the model is unavailable:

```powershell
ollama list
ollama ps
ollama run qwen3:1.7b 'Reply with OK'
```

If port 8000 is busy, locate the owner without killing it blindly:

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,State,OwningProcess
```

If an upload is rejected, confirm it is a searchable, unencrypted PDF below the
configured size/page limit. Scanned PDFs require OCR, which is not implemented.

If an evaluation fails, keep the workspace and show the explicit error. Check the API
terminal, `ollama ps`, and `reports/audit_log.jsonl`. Do not substitute a fabricated
result.

## 5. Backup and recovery

The demo PDFs are versioned source. Runtime uploads/results are under `storage/` and
draft reports/audit records are under `reports/`; both directories are Git-ignored.
With the API stopped, make a private local backup:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$destination = Join-Path $env:TEMP "TenderGuard-demo-backup-$stamp"
New-Item -ItemType Directory -Path $destination | Out-Null
if (Test-Path storage) { Copy-Item storage -Destination $destination -Recurse }
if (Test-Path reports) { Copy-Item reports -Destination $destination -Recurse }
Write-Host "Private backup: $destination"
```

Treat this backup as procurement data: do not email it, commit it, or place it in a
public cloud bucket. Recovery is copying the preserved `storage` and `reports`
directories back to the same project root while the API is stopped.

## 6. Screen recording

- Use Windows Snipping Tool screen recording or OBS configured for the TenderGuard
  browser window only.
- Hide terminals while passwords/environment variables are being entered.
- Disable notifications and close email, chat, AWS billing, and unrelated browser tabs.
- Record at 1080p, move the pointer slowly, and zoom the browser to keep citations
  readable.
- Begin recording only after sign-in; never record passwords, API keys, AWS account
  numbers, or real documents.
- Label any rehearsal recording as a rehearsal. Do not present it as a live run.

## 7. Shutdown checklist

- Download only the intended synthetic draft report.
- Sign out, stop Uvicorn with `Ctrl+C`, and close the terminal to clear its environment.
- Confirm no server is listening on port 8000.
- Store or remove private runtime data according to the demo retention decision.
- If AWS was separately approved, follow `deploy/aws/README.md`; stopping containers
  does not stop EC2/EBS/public IPv4 charges.
