"""Verify a public demo from an independent CI runner without sending credentials."""

import argparse
import json
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen

from deploy.temporary_demo import parse_deadline


def public_origin(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port
        or not parsed.hostname
        or not parsed.hostname.endswith(".trycloudflare.com")
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Use the public Quick Tunnel HTTPS origin without credentials or a path.")
    return f"https://{parsed.hostname}"


def probe(origin: str) -> dict:
    origin = public_origin(origin)
    with urlopen(origin + "/", timeout=25) as response:
        if response.status != 200 or "TenderGuard Africa" not in response.read().decode():
            raise RuntimeError("The external dashboard check failed.")
    with urlopen(origin + "/api/health", timeout=25) as response:
        health = json.load(response)
        if response.status != 200 or health.get("service") != "tenderguard-africa":
            raise RuntimeError("The external backend health check failed.")
    try:
        with urlopen(origin + "/api/browser/reports", timeout=25):
            raise RuntimeError("The external unauthenticated report check failed.")
    except HTTPError as exc:
        if exc.code != 401:
            raise RuntimeError("Unexpected unauthenticated report status.") from None
    return {
        "public_https_dashboard": 200,
        "public_https_backend": 200,
        "unauthenticated_reports": 401,
        "credentials_sent": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--until", required=True)
    args = parser.parse_args()
    deadline = parse_deadline(args.until)
    if datetime.now(UTC) >= deadline:
        print("External demo probe skipped: the explicitly scheduled demo window has ended.")
        return
    print(json.dumps(probe(args.url)))


if __name__ == "__main__":
    main()
