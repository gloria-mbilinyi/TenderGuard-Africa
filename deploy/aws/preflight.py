"""Read-only AWS identity, regional capacity, and On-Demand price inspection.

Run in an authenticated AWS CloudShell or AWS CLI session. No resource creation,
Cost Explorer calls, or credential export is performed. Credit coverage and organizer
authorization still require separate verification before any launch.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from decimal import Decimal
from typing import Any

REGION = "eu-north-1"
CANDIDATES = ["m7i-flex.large", "t3.large"]


def aws_read(*arguments: str, region: str = REGION) -> dict[str, Any]:
    command = shutil.which("aws")
    if not command:
        return {"error": "AWS_CLI_UNAVAILABLE"}
    try:
        result = subprocess.run(
            [command, *arguments, "--region", region, "--output", "json", "--no-cli-pager"],
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
            env={**os.environ, "AWS_PAGER": ""},
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"error": "AWS_REQUEST_UNAVAILABLE"}
    if result.returncode:
        code = re.search(r"An error occurred \(([A-Za-z0-9]+)\)", result.stderr)
        return {"error": code.group(1) if code else "AWS_AUTH_OR_REQUEST_FAILED"}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "AWS_RESPONSE_INVALID"}
    return payload if isinstance(payload, dict) else {"error": "AWS_RESPONSE_INVALID"}


def hourly_rate(pricing: dict[str, Any], unit: str = "Hrs") -> Decimal | None:
    rates = set()
    for entry in pricing.get("PriceList", []):
        product = json.loads(entry) if isinstance(entry, str) else entry
        for term in product.get("terms", {}).get("OnDemand", {}).values():
            for dimension in term.get("priceDimensions", {}).values():
                value = dimension.get("pricePerUnit", {}).get("USD")
                if dimension.get("unit") == unit and value is not None:
                    rates.add(Decimal(value))
    return next(iter(rates)) if len(rates) == 1 else None


def quote(instance_type: str) -> dict[str, Any]:
    filters = {
        "instanceType": instance_type,
        "location": "EU (Stockholm)",
        "operatingSystem": "Linux",
        "tenancy": "Shared",
        "preInstalledSw": "NA",
        "capacitystatus": "Used",
    }
    prices = aws_read(
        "pricing",
        "get-products",
        "--service-code",
        "AmazonEC2",
        "--filters",
        *(f"Type=TERM_MATCH,Field={key},Value={value}" for key, value in filters.items()),
        region="us-east-1",
    )
    rate = hourly_rate(prices)
    return {
        "hourly_compute_usd": str(rate) if rate is not None else None,
        "pricing_error": prices.get("error"),
    }


def inspect_account() -> dict[str, Any]:
    report: dict[str, Any] = {
        "checked_at": datetime.now().astimezone().isoformat(),
        "region": REGION,
        "credit_coverage_verified": False,
        "launch_authorized": False,
        "manual_checks_required": [
            "Billing Credits: current balance, eligible services, conditions, expiration",
            "Bills: current Support+, Bedrock, EC2, EBS, and IPv4 charges",
            "Account Free/Paid plan restrictions and organizer resource-creation rules",
            "Approved budget email, incremental cost, and UTC shutdown time",
        ],
    }
    report["identity"] = aws_read("sts", "get-caller-identity")
    if "error" in report["identity"]:
        return report
    report["account_aliases"] = aws_read("iam", "list-account-aliases")
    types = aws_read("ec2", "describe-instance-types", "--instance-types", *CANDIDATES)
    report["instance_types"] = (
        [
            {
                "type": item["InstanceType"],
                "vcpu": item["VCpuInfo"]["DefaultVCpus"],
                "memory_mib": item["MemoryInfo"]["SizeInMiB"],
                "architectures": item["ProcessorInfo"]["SupportedArchitectures"],
                "free_tier_eligible": item.get("FreeTierEligible"),
            }
            for item in types.get("InstanceTypes", [])
        ]
        if "error" not in types
        else types
    )
    report["offerings"] = aws_read(
        "ec2",
        "describe-instance-type-offerings",
        "--location-type",
        "region",
        "--filters",
        f"Name=instance-type,Values={','.join(CANDIDATES)}",
    )
    inventory = aws_read("ec2", "describe-instances")
    report["existing_instances"] = (
        [
            {
                "instance_id": instance["InstanceId"],
                "name": next(
                    (tag["Value"] for tag in instance.get("Tags", []) if tag["Key"] == "Name"), ""
                ),
                "type": instance.get("InstanceType"),
                "state": instance.get("State", {}).get("Name"),
            }
            for reservation in inventory.get("Reservations", [])
            for instance in reservation.get("Instances", [])
        ]
        if "error" not in inventory
        else inventory
    )
    report["on_demand_compute_quotes"] = {kind: quote(kind) for kind in CANDIDATES}
    report["public_ipv4_hourly_usd"] = "0.005"
    report["public_ipv4_price_source"] = "https://aws.amazon.com/vpc/pricing/"
    report["cost_exclusions"] = "EBS, tax, transfer, snapshots, support, and other existing usage"
    return report


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    report = inspect_account()
    print(json.dumps(report, indent=2))
    if "error" in report["identity"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
