"""Real TLS/PDF/model/persistence smoke test for an isolated validation stack.

The caller starts the test-only Compose stack. No AWS resource is created. The local
Caddy CA is explicitly trusted for this test; certificate verification stays enabled.
All credentials are ephemeral test values supplied through the process environment.
"""

import argparse
import json
import os
import re
import ssl
import subprocess
import time
from pathlib import Path

import httpx

from deploy.aws.verify_cloud import (
    require_status,
    verify_evaluation,
    verify_login,
    verify_report,
)

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "https://localhost:8443"


def compose(project: str, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
    if not re.fullmatch(r"tg-verify-[a-f0-9]{12}", project):
        raise ValueError("Smoke tests require a dedicated tg-verify-* Compose project.")
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            project,
            "-f",
            str(ROOT / "deploy/aws/compose.aws.yaml"),
            "-f",
            str(ROOT / "deploy/validation/compose.validation.yaml"),
            *arguments,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    if check and result.returncode:
        # Do not echo Docker output, which may contain environment configuration.
        raise RuntimeError(f"Validation Compose operation failed: {arguments[0]}.")
    return result


def await_health(client: httpx.Client) -> None:
    for _ in range(60):
        try:
            if client.get("/api/health").status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(1)
    raise RuntimeError("TLS/backend health did not become ready.")


def run(project: str, ca_file: Path) -> None:
    password = os.environ["TENDERGUARD_DASHBOARD_PASSWORD"]
    context = ssl.create_default_context(cafile=ca_file)
    with httpx.Client(base_url=ORIGIN, verify=context, timeout=30) as client:
        await_health(client)
        csrf = verify_login(client, ORIGIN, password)
        # CSRF and origin protections must remain active over the reverse proxy.
        require_status(
            client.post(
                "/api/browser/document-evaluations",
                json={"title": "blocked"},
                headers={"Origin": ORIGIN},
            ),
            403,
            "Missing CSRF rejected",
        )
        require_status(
            client.post(
                "/api/browser/document-evaluations",
                json={"title": "blocked"},
                headers={"Origin": "https://untrusted.invalid", "X-CSRF-Token": csrf},
            ),
            403,
            "Untrusted origin rejected",
        )
        workspace = verify_evaluation(client, ORIGIN, csrf)
        filename = f"{workspace}_evaluation_report.md"
        items = client.get("/api/browser/reports").json()["reports"]
        if any(item["filename"] == filename for item in items):
            raise RuntimeError("A report was created without separate authorization.")
        denied = compose(
            project,
            "exec",
            "-T",
            "tenderguard",
            "python",
            "-m",
            "app.agent.approve_documents",
            "--workspace",
            workspace,
            "--approved-by",
            "",
            check=False,
        )
        if denied.returncode == 0:
            raise RuntimeError("Blank report authorization was accepted.")
        compose(
            project,
            "exec",
            "-T",
            "tenderguard",
            "python",
            "-m",
            "app.agent.approve_documents",
            "--workspace",
            workspace,
            "--approved-by",
            "Synthetic CI Reviewer",
        )
        verify_report(client, workspace)
        saved = client.get(f"/api/browser/document-evaluations/{workspace}/result").json()

        # A new application container must preserve PDF workspaces and authorized reports.
        compose(project, "up", "-d", "--no-deps", "--force-recreate", "tenderguard")
        client.cookies.clear()
        await_health(client)
        csrf = verify_login(client, ORIGIN, password)
        restored = require_status(
            client.get(f"/api/browser/document-evaluations/{workspace}/result"),
            200,
            "Persisted evaluation",
        ).json()
        if restored != saved:
            raise RuntimeError("Evaluation evidence changed after container replacement.")
        verify_report(client, workspace)
        require_status(
            client.post(
                "/api/browser/logout",
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": csrf,
                },
            ),
            204,
            "Logout",
        )
        require_status(
            client.get(f"/api/browser/reports/{filename}/download"),
            401,
            "Logged-out report access blocked",
        )
    print(
        json.dumps(
            {
                "tls_verified": True,
                "pdf_count": 3,
                "supplier_count": 2,
                "persistence_verified": True,
                "report_authorization_verified": True,
                "human_committee_required": True,
                "final_award_decision": None,
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--ca-file", type=Path, required=True)
    args = parser.parse_args()
    run(args.project, args.ca_file)


if __name__ == "__main__":
    main()
