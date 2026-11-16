# Downloadable TenderGuard Procurement MCP

TenderGuard can operate as a standalone web application or as a local stdio MCP
server. The MCP package exposes bounded procurement and uploaded-document tools. It
does not expose a general filesystem, a browser approval action, or an award tool.

## Install on Windows

```powershell
git clone <APPROVED_TENDERGUARD_REPOSITORY_URL>
Set-Location TenderGuard-Africa
git switch nairobi-demo-prep
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
ollama pull qwen3:1.7b
```

Set document storage to a private directory outside the source tree if desired:

```powershell
$env:TENDERGUARD_DOCUMENT_STORAGE = 'C:\TenderGuardData\document_evaluations'
$env:TENDERGUARD_OLLAMA_URL = 'http://127.0.0.1:11434/api/chat'
$env:TENDERGUARD_OLLAMA_MODEL = 'qwen3:1.7b'
.\.venv\Scripts\tenderguard-procurement-mcp.exe
```

The command speaks MCP over stdio. It is expected to appear idle when launched without
an MCP client.

## Install on Linux

```bash
git clone <APPROVED_TENDERGUARD_REPOSITORY_URL>
cd TenderGuard-Africa
git switch nairobi-demo-prep
python3.12 -m venv .venv
./.venv/bin/python -m pip install .
ollama pull qwen3:1.7b
export TENDERGUARD_DOCUMENT_STORAGE="$HOME/.local/share/tenderguard/document_evaluations"
export TENDERGUARD_OLLAMA_URL="http://127.0.0.1:11434/api/chat"
./.venv/bin/tenderguard-procurement-mcp
```

## Exposed MCP tools

The server retains the original structured synthetic-data tools and adds:

- `create_document_evaluation_workspace`
- `ingest_pdf_document`
- `get_document_evaluation_status`
- `load_document_workspace`
- `evaluate_document_workspace`
- `run_document_agent_evaluation`
- `get_document_evaluation_result`
- `generate_document_evaluation_report`

`ingest_pdf_document` accepts base64 PDF bytes, not an arbitrary server-side file
path. The same size, page, signature, encryption, active-content, boundary, and
searchable-text validations used by FastAPI apply. The PDF payload itself is not
written to the audit log.

`run_document_agent_evaluation` invokes the real LangGraph, Procurement MCP, and
Ollama pipeline. It must end at `AWAITING_HUMAN_REVIEW` with a null award decision.
The report-generation tool still requires a named human authorization string; this is
a local demonstration control, not verified identity.

## Actual MCP client verification

Run the repository's MCP tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_mcp_client.py tests\test_document_mcp.py -q
```

Or run the supplied real client against the synthetic PDFs:

```powershell
.\.venv\Scripts\python.exe examples\mcp_document_client.py `
  --tender demo_documents\tender_requirements_synthetic.pdf `
  --bid demo_documents\alpha_supplier_bid_synthetic.pdf `
  --bid demo_documents\beta_supplier_bid_synthetic.pdf
```

## Claude Desktop example

Copy [`config/claude_desktop_config.example.json`](../config/claude_desktop_config.example.json)
into your Claude Desktop configuration and replace both absolute paths. Do not add API
keys or dashboard passwords. Restart Claude Desktop and inspect its MCP tool list.

The stdio protocol and tool discovery are verified with the official MCP Python client
in this repository. Claude Desktop itself was not available in the development
environment, so client-specific compatibility must be verified on the target laptop
before the Nairobi demonstration.

## ChatGPT compatibility boundary

This package exposes local stdio MCP. It does not claim direct ChatGPT connector
compatibility. That would require a separately secured remote MCP transport,
authentication, HTTPS, and platform-specific testing. Do not expose this stdio server
directly to the public internet.

## Docker distribution

The main Docker image contains the Procurement MCP server and the pinned borrowed
Filesystem MCP server. The Filesystem MCP remains read-only and confined to `reports/`.
See [DOCKER_INSTALLATION.md](DOCKER_INSTALLATION.md). Uploaded PDFs use a separate
`tenderguard_documents` volume.
