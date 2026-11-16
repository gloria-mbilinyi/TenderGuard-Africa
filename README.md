# TenderGuard Africa

**Agentic AI procurement decision-support system for auditable public tender evaluation in African institutions.**

TenderGuard Africa uses an open-weights model, LangGraph, and Model Context Protocol (MCP) tools to review tender evidence, check mandatory compliance, compare prices with historical procurement data, identify supplier-data inconsistencies, and prepare a sourced evaluation report.

The system does **not** award tenders. It prepares evidence and stops for human procurement committee review.

---

## Challenge

TenderGuard Africa was built for the **Governance Track** of the **African Agentic AI Design Challenge – The Bid Box Challenge**.

**Theme:** Digital Economy – Open Contracting

---

## Problem Statement

Public procurement teams may spend significant time manually sorting tender records, checking mandatory documents, verifying eligibility requirements, comparing bid prices, reviewing supplier information, and preparing evaluation reports.

This process is repetitive and time-consuming. It can also become difficult to audit when evidence is distributed across multiple procurement records and reviewers must manually trace how each conclusion was reached.

TenderGuard Africa addresses this workflow bottleneck by automating evidence preparation and procurement decision support while preserving human accountability.

The AI agent can analyse evidence and highlight findings, but it cannot select a winning bidder or make a final procurement award.

---

## Solution Overview

TenderGuard Africa is an agentic procurement decision-support system that prepares evidence for public tender evaluation.

It uses a locally hosted open-weights model to plan the evaluation workflow, while LangGraph coordinates a sequence of MCP tools that:

1. load tender evidence;
2. check mandatory bid compliance;
3. compare submitted prices with historical award data;
4. review supplier-data inconsistencies;
5. synthesize sourced findings;
6. stop for human review.

The autonomous workflow ends at:

```text
AWAITING_HUMAN_REVIEW
```

A named human reviewer must approve the consequential report-generation action before a draft evaluation report can be created.

The authorised procurement committee retains the final procurement decision.

---

## Target Users

TenderGuard Africa is designed for:

- public procurement officers;
- tender evaluation committees;
- procurement auditors;
- public-sector oversight bodies;
- anti-corruption and accountability institutions;
- public institutions managing competitive procurement.

The system is intended to reduce repetitive evidence-preparation work while keeping consequential procurement decisions under human control.

---

## What the Agent Does

The TenderGuard agent:

1. Plans the tender evaluation workflow.
2. Loads tender evidence.
3. Checks mandatory bid compliance.
4. Compares submitted prices with historical award data.
5. Reviews supplier-data inconsistencies.
6. Synthesizes sourced findings.
7. Assigns a review priority based on collected evidence.
8. Stops at human review.
9. Generates a draft evaluation report only after named human approval.
10. Leaves the final procurement decision to the authorised human committee.

TenderGuard never automatically:

- awards a tender;
- rejects a bidder;
- disqualifies a bidder;
- selects a winning bidder;
- makes a final procurement decision.

---

## Key Agentic Capabilities

TenderGuard demonstrates:

- planning;
- reasoning;
- decision support;
- MCP tool calling;
- data retrieval;
- multi-step execution;
- workflow automation;
- recommendation generation;
- information synthesis;
- structured output validation;
- failure handling and retries;
- human-in-the-loop approval;
- auditable tool execution.

---

## One-Command Demo

### Prerequisites

Install:

- Python 3.12
- Git
- Node.js and npm
- Ollama

The project uses the local open-weights model:

```text
qwen3:1.7b
```

### Run

From the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

The script:

- creates the Python virtual environment if necessary;
- activates the environment;
- installs project dependencies;
- checks for Ollama;
- downloads Qwen3 1.7B if necessary;
- starts the TenderGuard evaluation demo.

The demo evaluates the synthetic problematic bid:

```text
TG-DEMO-001
BID-BETA-001
```

The workflow should finish at:

```text
AWAITING_HUMAN_REVIEW
```

This is intentional. The autonomous agent is not allowed to continue to a procurement award.

---

## Professional Web Dashboard

Phase 3 adds a responsive React and TypeScript dashboard backed by the real FastAPI,
LangGraph, Procurement MCP, and Ollama workflow. It includes synthetic tender and bid
selection, validated evidence views, recent evaluation activity, protected draft
report downloads, dark mode, and sanitized local-service status.

The browser does not contain or receive `TENDERGUARD_API_KEY`. It signs in through a
separate server-side local session using an `HttpOnly`, `SameSite=Strict` cookie and
CSRF protection. This is a single-operator local demo control, not production identity
or institutional role-based access control.

For local development:

```powershell
$env:TENDERGUARD_DASHBOARD_PASSWORD = "replace-with-a-private-password"
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. See
[`docs/WEB_DASHBOARD.md`](docs/WEB_DASHBOARD.md) for the complete development,
production-build, Docker, authentication, and security-boundary guide.

### Searchable PDF supplier comparison

The authenticated **PDF workspaces** page accepts one tender requirements PDF and at
least two supplier bid PDFs. It validates and extracts searchable documents, shows
safe previews, executes the real Qwen/LangGraph/Procurement MCP workflow, and presents
page-cited supplier findings. The autonomous result always stops at human review and
never contains an award.

The repository includes three visibly synthetic demonstration PDFs. A CLI run of the
same workflow is:

```powershell
.\.venv\Scripts\python.exe -m app.agent.run_documents `
  --tender demo_documents\tender_requirements_synthetic.pdf `
  --bid demo_documents\alpha_supplier_bid_synthetic.pdf `
  --bid demo_documents\beta_supplier_bid_synthetic.pdf
```

See [PDF evaluation](docs/PDF_EVALUATION.md), the
[Nairobi demo runbook](docs/NAIROBI_DEMO_RUNBOOK.md), and the
[downloadable MCP guide](docs/MCP_INSTALLATION.md).

---

## Docker Quick Start

Docker packages the production dashboard, FastAPI application, LangGraph workflow,
Procurement MCP server, and borrowed Filesystem MCP server as a self-hosted agent. It
uses only free and open-source runtime components. The dashboard and API are published
on `127.0.0.1` by default, and every autonomous evaluation still stops at
`AWAITING_HUMAN_REVIEW`.

Prerequisites:

- Docker Desktop on Windows, or Docker Engine with the Compose plugin on Linux;
- either Ollama on the host, or the optional Ollama Compose profile;
- enough disk space for the container images and `qwen3:1.7b` model.

From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
$apiKey = [guid]::NewGuid().ToString("N")
(Get-Content .env) -replace '^TENDERGUARD_API_KEY=.*$', "TENDERGUARD_API_KEY=$apiKey" | Set-Content .env
(Get-Content .env) -replace '^TENDERGUARD_DASHBOARD_PASSWORD=.*$', 'TENDERGUARD_DASHBOARD_PASSWORD=replace-with-a-private-password' | Set-Content .env
ollama pull qwen3:1.7b
docker compose build
docker compose up -d
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Open `http://127.0.0.1:8000` after the health check succeeds.

The default `.env.example` connects the container to host Ollama through
`host.docker.internal`. To use Dockerized Ollama instead, set
`TENDERGUARD_OLLAMA_URL=http://ollama:11434/api/chat`, start the `ollama` profile,
and pull the model into its persistent volume once:

```powershell
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull qwen3:1.7b
docker compose --profile ollama up -d
```

Model downloads are deliberately not part of application startup. Named volumes keep
uploaded documents, reports, audit records, and Dockerized Ollama models across
ordinary restarts. See
[`docs/DOCKER_INSTALLATION.md`](docs/DOCKER_INSTALLATION.md) for the complete Windows
and Linux setup, API evaluation command, persistence checks, and troubleshooting.

The first installation requires internet access to download images, dependencies, and
the model. Do not assume fully offline operation until those artifacts have been
downloaded and the deployment has been tested locally.

---

## Manual Setup

Create and activate the Python environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install TenderGuard and development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Download the local open-weights model:

```powershell
ollama pull qwen3:1.7b
```

Run the evaluation agent:

```powershell
python -m app.agent.run --tender TG-DEMO-001 --bid BID-BETA-001
```

To run the web dashboard, follow the two-terminal development steps above or build
`frontend/` and let FastAPI serve `frontend/dist` on port 8000.

---

## Human Approval and Report Generation

After reviewing the agent findings, a named human reviewer can approve generation of the draft evaluation report:

```powershell
python -m app.agent.approve --tender TG-DEMO-001 --bid BID-BETA-001 --approved-by "Demo Procurement Reviewer"
```

The generated report is written under:

```text
reports/
```

The report is marked:

```text
DRAFT_FOR_COMMITTEE_REVIEW
```

The report-generation action does not constitute an award decision.

The human procurement committee remains responsible for the final decision.

---

## Architecture

The high-level TenderGuard data flow is:

```text
Synthetic Procurement Data
        |
        v
Qwen3 1.7B Planning
        |
        v
LangGraph Orchestration
        |
        v
MCP Client
        |
        v
TenderGuard Procurement MCP
        |
        +--> load_tender
        |
        +--> check_bid_compliance
        |
        +--> compare_prices
        |
        +--> flag_supplier_risk
        |
        v
Qwen3 Evidence Synthesis
        |
        v
AWAITING_HUMAN_REVIEW
        |
        v
Named Human Approval
        |
        v
generate_evaluation_report
        |
        v
Draft Evaluation Report
        |
        v
Filesystem MCP Read / Verification
        |
        v
Human Procurement Committee
```

The custom TenderGuard Procurement MCP server and the borrowed Filesystem MCP server do not communicate directly with each other.

The application interacts with them through separate MCP client operations.

See:

```text
ARCHITECTURE.md
```

for the detailed system architecture.

---

## Agent Architecture

TenderGuard uses a stateful agent architecture composed of the following layers.

### Open-Weights Reasoning Layer

TenderGuard uses:

```text
qwen3:1.7b
```

through Ollama.

The model performs:

- workflow planning;
- evidence synthesis.

Structured model responses are validated using Pydantic.

### Orchestration Layer

LangGraph manages the multi-step evaluation workflow and agent state.

The workflow tracks information such as:

- tender ID;
- bid ID;
- planned MCP tools;
- completed tools;
- compliance findings;
- price-analysis findings;
- supplier-risk findings;
- evidence summary;
- review priority;
- workflow status.

The graph also supports controlled retries for recoverable MCP execution failures.

### Tool Execution Layer

Procurement capabilities are accessed through Model Context Protocol.

The agent communicates with the custom Procurement MCP server using an MCP client session instead of directly importing and calling procurement tool functions.

### Safety Layer

A deterministic evidence guard checks the actual tool findings before assigning review priority.

The system always preserves:

```text
human_committee_required = true
```

and:

```text
final_award_decision = null
```

during autonomous evaluation.

---

## Model Context Protocol Implementation

TenderGuard uses Model Context Protocol as the execution boundary between the LangGraph workflow and procurement tools.

The application creates an MCP client session and communicates with the custom TenderGuard Procurement MCP server over stdio.

Procurement capabilities are invoked through MCP tool calls rather than by the agent directly calling the underlying Python procurement functions.

This architecture separates:

- AI reasoning;
- workflow orchestration;
- tool execution;
- human approval;
- file operations.

The project uses two MCP servers:

1. a custom TenderGuard Procurement MCP server;
2. a borrowed Filesystem MCP server.

---

## Custom MCP Server

TenderGuard includes its own MCP server:

```text
TenderGuard Procurement MCP
```

It exposes the original structured-data tools plus bounded uploaded-document tools.

### `load_tender`

Loads and normalizes tender records together with source information.

### `check_bid_compliance`

Checks mandatory tender requirements including:

- submission deadline;
- mandatory documents;
- eligibility requirements.

Each finding contains source evidence.

### `compare_prices`

Compares a submitted bid price with historical award values.

It returns information including:

- historical minimum;
- historical median;
- historical maximum;
- percentage deviation;
- risk classification;
- source evidence.

### `flag_supplier_risk`

Reviews supplier-history records and identifies data inconsistencies that may require human attention.

These findings are indicators for further review.

They are not accusations of fraud or misconduct.

### `generate_evaluation_report`

Generates a sourced draft evaluation report.

This is a consequential action tool.

It requires:

```text
approved_by
```

to contain the name of a human approver.

Without named human approval, report generation is blocked.

The tool does not award or reject a tender.

### Uploaded-document tools

`create_document_evaluation_workspace`, `ingest_pdf_document`, and
`get_document_evaluation_status` manage one isolated tender-plus-bids workspace without
accepting arbitrary server filesystem paths. `load_document_workspace` and
`evaluate_document_workspace` provide deterministic, page-cited evidence to the real
LangGraph workflow. `run_document_agent_evaluation` executes that workflow through
Ollama, while `get_document_evaluation_result` returns only the completed human-review
result. `generate_document_evaluation_report` retains the separate named-human draft
report gate and never makes an award.

---

## Borrowed MCP Server

TenderGuard also integrates:

```text
@modelcontextprotocol/server-filesystem
```

This server was not written as part of TenderGuard Africa.

It provides reusable filesystem operations and access controls.

The TenderGuard integration restricts this server to:

```text
reports/
```

It is used to:

- list report files;
- read generated reports;
- verify report output.

The borrowed Filesystem MCP does not make procurement decisions and does not communicate directly with the custom Procurement MCP server.

---

## Human-in-the-Loop Workflow

Human oversight is a mandatory part of TenderGuard's architecture.

The autonomous evaluation workflow stops at:

```text
AWAITING_HUMAN_REVIEW
```

TenderGuard does not contain an automated tender-award node.

After reviewing the findings, a named human may approve draft report generation.

The flow is:

```text
Agent Analysis
      |
      v
AWAITING_HUMAN_REVIEW
      |
      v
Human Reviewer
      |
      | Named approval
      v
Draft Report Generation
      |
      v
Human Procurement Committee
      |
      v
Final Procurement Decision
```

The final decision is always outside the autonomous agent.

---

## Open-Weights Model

A complete TenderGuard evaluation workflow runs locally using:

```text
qwen3:1.7b
```

through Ollama.

The model performs both:

- planning;
- evidence synthesis.

No closed frontier model is required to complete the core evaluation workflow.

Running the model locally also supports stronger data-sovereignty options for institutions that may not want procurement records sent to an external cloud LLM provider.

---

## Audit Trail

Custom MCP actions are logged.

Audit records include:

- timestamp;
- tool name;
- inputs;
- outputs;
- execution status;
- human approver where applicable.

Runtime audit records are stored under:

```text
reports/
```

This creates a traceable record of how the evaluation workflow was executed.

Generated runtime logs and reports are excluded from Git tracking.

---

## Data Sources

The current prototype uses synthetic procurement records.

```text
data/
├── ocds/
└── synthetic_bids/
```

The dataset contains:

- synthetic tender records;
- synthetic bid records;
- historical award reference records;
- supplier-history records.

Tender and historical records use procurement and OCDS-style fields.

The repository does not claim that the current records are live Tanzanian procurement records.

Synthetic data is used so that the public repository does not expose:

- live tender-in-progress information;
- real bidder confidential information;
- personal information.

Real public OCDS-compatible releases can be integrated in a future deployment.

---

## Demo Dataset

The main demonstration tender is:

```text
Tender ID: TG-DEMO-001
Title: Supply of Computer Equipment
Estimated Value: TZS 45,000,000
```

Two synthetic bids are included.

### Alpha Technologies

```text
Bid ID: BID-ALPHA-001
Price: TZS 42,000,000
```

The synthetic record is designed to satisfy the mandatory tender requirements.

### Beta Systems

```text
Bid ID: BID-BETA-001
Price: TZS 47,000,000
```

The synthetic record intentionally includes issues that allow the agent to demonstrate:

- late-submission detection;
- missing mandatory-document detection;
- eligibility checking;
- elevated price comparison;
- supplier-data inconsistency detection;
- human review escalation.

---

## Evaluation

TenderGuard includes 10 documented evaluation tasks.

Current evaluation results:

```text
9 PASS
1 known FAIL
```

Passing evaluations cover:

1. compliant-bid full agent workflow;
2. problematic-bid full agent workflow;
3. custom MCP tool discovery;
4. compliance detection;
5. historical price-anomaly detection;
6. supplier-data inconsistency detection;
7. human approval enforcement;
8. filesystem sandbox enforcement;
9. open-model planner repeatability.

The intentionally disclosed unresolved failure is:

```text
Image-only/scanned PDF extraction
```

OCR is not implemented in the current prototype.

The failure is documented rather than hidden because evaluation reliability and known limitations are part of the project design.

See:

```text
EVALS.md
```

for the complete evaluation report.

---

## Tests

Run the automated test suite:

```powershell
pytest -q
```

Run frontend tests and a production build:

```powershell
Set-Location frontend
npm test
npm run build
```

Run the full evaluation suite:

```powershell
python -m evals.run_evals
```

---

## Project Structure

The Phase 3 additions are `frontend/` for the React application, `app/services/` for
catalog/result/report boundaries, and the authenticated browser routes under
`app/api/`.

```text
TenderGuard-Africa/
├── app/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── approve.py
│   │   ├── filesystem_mcp.py
│   │   ├── mcp_client.py
│   │   ├── ollama_client.py
│   │   ├── run.py
│   │   ├── state.py
│   │   └── workflow.py
│   ├── api/
│   │   └── __init__.py
│   └── ui/
│
├── mcp_servers/
│   ├── __init__.py
│   └── procurement/
│       ├── __init__.py
│       ├── audit.py
│       ├── server.py
│       └── tools/
│           ├── __init__.py
│           ├── load_tender.py
│           ├── check_bid_compliance.py
│           ├── compare_prices.py
│           ├── flag_supplier_risk.py
│           └── generate_evaluation_report.py
│
├── data/
│   ├── ocds/
│   │   ├── demo_tender.json
│   │   ├── historical_awards.json
│   │   └── supplier_history.json
│   └── synthetic_bids/
│       ├── bid_alpha.json
│       └── bid_beta.json
│
├── evals/
│   ├── __init__.py
│   ├── run_evals.py
│   └── results.json
│
├── reports/
├── tests/
├── ARCHITECTURE.md
├── EVALS.md
├── LICENSE
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
└── start.ps1
```

---

## Technology Stack

### Artificial Intelligence

- Qwen3 1.7B
- Ollama

### Agent Orchestration

- LangGraph

### Model Context Protocol

- MCP Python SDK
- TenderGuard Procurement MCP
- `@modelcontextprotocol/server-filesystem`

### Backend and Validation

- Python 3.12
- FastAPI
- Pydantic
- HTTPX

### Web Dashboard

- React 19
- TypeScript
- Vite
- Tailwind CSS
- Lucide React

### Document Support

- PyPDF

PyPDF is included for document-processing support, but image-only/scanned PDF OCR is not implemented in the current prototype.

### Testing

- Pytest
- Vitest
- Testing Library

### Supporting Runtime

- Node.js
- npm / npx

### Development and Version Control

- Git
- GitHub

---

## Known Limitations

### Scanned Documents

Image-only and scanned PDF bid documents are not currently supported because the prototype does not include OCR.

### Current Data Scope

The current demonstration uses structured synthetic procurement records rather than live bidder submissions.

### User Interface

The dashboard password and in-memory session store are appropriate for a local,
single-operator demonstration. Production deployment requires durable identity,
role-based authorization, HTTPS, rate limiting, and multi-user session controls.

---

## Future Improvements

Future versions of TenderGuard Africa could include:

- ingestion of real public OCDS-compatible procurement releases;
- structured extraction from PDF tender documents;
- structured extraction from DOCX bid documents;
- OCR support for scanned and image-only records;
- page-level evidence citations;
- extraction-confidence scoring;
- human validation of low-confidence extracted fields;
- additional procurement-risk indicators;
- persistent database storage;
- institutional identity and role-based access control;
- durable database-backed sessions and evaluation history;
- institution-specific procurement rules;
- multilingual procurement support;
- integrations with public procurement portals where lawful and technically available.

---

## Safety and Procurement Principle

> **TenderGuard Africa prepares the evaluation file. The human procurement committee decides.**

The system is designed as decision support, not decision replacement.

---

## Repository

Public repository:

```text
https://github.com/prettyglory/TenderGuard-Africa
```

---

## License

TenderGuard Africa is released under the MIT License.

See:

```text
LICENSE
```

for details.
