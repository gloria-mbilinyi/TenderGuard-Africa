"""Verify real HTTPS login, PDF evaluation, and protected report download.

Run from the repository with its Python environment. The initial run creates a new
synthetic evaluation and stops for separate administrator CLI report authorization.
Then use --workspace WORKSPACE --report-only to verify the resulting draft download.
Passwords are prompted privately and are never written to output files or arguments.
"""

import argparse
import getpass
import secrets
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx

from app.api.models import DocumentEvaluationResponse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDFS = [
    ("tender_requirements_synthetic.pdf", "TENDER_REQUIREMENTS"),
    ("alpha_supplier_bid_synthetic.pdf", "SUPPLIER_BID"),
    ("beta_supplier_bid_synthetic.pdf", "SUPPLIER_BID"),
]


def https_origin(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Provide the exact HTTPS origin without credentials, paths, or queries.")
    return f"https://{parsed.netloc}"


def require_status(response: httpx.Response, expected: int, stage: str) -> httpx.Response:
    if response.status_code != expected:
        raise RuntimeError(f"{stage}: expected HTTP {expected}, received {response.status_code}.")
    return response


def verify_login(client: httpx.Client, origin: str, password: str) -> str:
    require_status(client.get("/api/health"), 200, "HTTPS backend health")
    require_status(client.get("/api/browser/reports"), 401, "Unauthenticated reports blocked")
    require_status(
        client.post(
            "/api/browser/session",
            headers={"Origin": origin},
            json={"password": secrets.token_urlsafe(40)},
        ),
        401,
        "Invalid login rejected",
    )
    login = require_status(
        client.post(
            "/api/browser/session",
            headers={"Origin": origin},
            json={"password": password},
        ),
        200,
        "Dashboard login",
    )
    cookie = login.headers.get("set-cookie", "").lower()
    if not all(flag in cookie for flag in ["httponly", "secure", "samesite=strict"]):
        raise RuntimeError("Hosted login did not set the required secure session cookie flags.")
    print("HTTPS health, invalid login, secure session, and unauthorized report checks passed.")
    return login.json()["csrf_token"]


def verify_evaluation(client: httpx.Client, origin: str, csrf: str) -> str:
    headers = {"Origin": origin, "X-CSRF-Token": csrf}
    workspace = require_status(
        client.post(
            "/api/browser/document-evaluations",
            headers=headers,
            json={"title": "Synthetic PDF deployment verification"},
        ),
        200,
        "Create workspace",
    ).json()
    workspace_id = workspace["workspace_id"]
    base = f"/api/browser/document-evaluations/{workspace_id}"
    for filename, kind in PDFS:
        uploaded = require_status(
            client.post(
                f"{base}/documents",
                params={"document_type": kind},
                headers={**headers, "Content-Type": "application/pdf", "X-File-Name": filename},
                content=(PROJECT_ROOT / "demo_documents" / filename).read_bytes(),
            ),
            200,
            "Upload searchable synthetic PDF",
        ).json()
        if any(
            document["extraction_status"] != "TEXT_EXTRACTED" for document in uploaded["documents"]
        ):
            raise RuntimeError("A synthetic PDF failed text extraction.")
    if uploaded["status"] != "READY_FOR_EVALUATION":
        raise RuntimeError("Uploaded workspace did not become ready.")
    response = require_status(
        client.post(
            f"{base}/evaluate",
            headers=headers,
            timeout=180,
        ),
        200,
        "Real Ollama/LangGraph/MCP evaluation",
    )
    result = DocumentEvaluationResponse.model_validate(response.json())
    if result.workspace_id != workspace_id or len(result.suppliers) != 2:
        raise RuntimeError("Evaluation returned an unexpected workspace or supplier count.")
    if result.completed_tools != ["load_document_workspace", "evaluate_document_workspace"]:
        raise RuntimeError("Expected Procurement MCP tools did not complete.")
    if not any("REQ-TAX-CLEARANCE" in supplier.missing_documents for supplier in result.suppliers):
        raise RuntimeError("Expected synthetic missing tax-clearance evidence was not identified.")
    findings = [
        finding
        for supplier in result.suppliers
        for finding in (
            *supplier.document_checks,
            *supplier.eligibility_checks,
            *supplier.technical_checks,
            supplier.financial_check,
        )
    ]
    if any(finding.code == "SUBMISSION_DEADLINE" or not finding.sources for finding in findings):
        raise RuntimeError("Unexpected deadline check or missing source citation.")
    if result.decision_support.review_priority != "ATTENTION_REQUIRED":
        raise RuntimeError("Synthetic missing evidence did not receive attention priority.")
    print(f"WORKSPACE={workspace_id}")
    print("Three PDFs extracted; two suppliers evaluated with page citations and MCP execution.")
    print("AWAITING_HUMAN_REVIEW; human_committee_required=true; final_award_decision=null.")
    print(
        "Generate the draft through the separate named administrator CLI gate, then run --report-only."
    )
    return workspace_id


def verify_report(client: httpx.Client, workspace_id: str) -> None:
    filename = f"{workspace_id}_evaluation_report.md"
    reports = require_status(
        client.get("/api/browser/reports"), 200, "Protected report list"
    ).json()
    if not any(item["filename"] == filename for item in reports["reports"]):
        raise RuntimeError(
            "Authorized draft is not available; complete the separate CLI authorization."
        )
    download = require_status(
        client.get(f"/api/browser/reports/{quote(filename, safe='')}/download"),
        200,
        "Protected draft download",
    )
    if "DRAFT FOR HUMAN PROCUREMENT COMMITTEE REVIEW" not in download.text:
        raise RuntimeError("Downloaded file lacks the committee-review draft marker.")
    print("Authorized report listing and protected draft download passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--workspace")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if args.report_only and not args.workspace:
        parser.error("--report-only requires the completed --workspace ID.")
    origin = https_origin(args.url)
    password = getpass.getpass("Private hosted dashboard password: ")
    with httpx.Client(base_url=origin, timeout=30, follow_redirects=False) as client:
        csrf = verify_login(client, origin, password)
        if args.report_only:
            verify_report(client, args.workspace)
        else:
            verify_evaluation(client, origin, csrf)
        require_status(
            client.post(
                "/api/browser/logout",
                headers={"Origin": origin, "X-CSRF-Token": csrf},
            ),
            204,
            "Logout",
        )
        require_status(client.get("/api/browser/reports"), 401, "Revoked session blocked")


if __name__ == "__main__":
    main()
