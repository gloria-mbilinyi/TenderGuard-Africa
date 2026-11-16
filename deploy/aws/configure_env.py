"""Create a private cloud .env without printing or overwriting credentials."""

import argparse
import getpass
import ipaddress
import os
import re
import secrets
from pathlib import Path


def validate_domain(domain: str) -> str:
    domain = domain.strip().lower()
    try:
        ipaddress.ip_address(domain)
    except ValueError:
        pass
    else:
        raise ValueError("Use a DNS hostname with a public TLS certificate, not a raw IP.")
    if (
        len(domain) > 253
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", domain)
        or "." not in domain
        or any(
            not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
            for label in domain.split(".")
        )
        or domain.endswith((".example.org", ".example.com", ".localhost"))
        or domain in {"example.org", "example.com"}
    ):
        raise ValueError("Set the actual public DNS hostname, without a scheme, path, or port.")
    return domain


def write_configuration(path: Path, domain: str, email: str, password: str) -> None:
    domain = validate_domain(domain)
    if not re.fullmatch(r"[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email):
        raise ValueError("A valid TLS notification email is required.")
    if (
        len(password) < 16
        or len(password) > 256
        or any(
            ord(character) < 32 or ord(character) > 126 or character in {"'", "\\"}
            for character in password
        )
    ):
        raise ValueError(
            "Use 16–256 printable ASCII characters, excluding single quotes/backslashes."
        )
    # Compose single-quoted .env values preserve dollar signs without interpolation.
    content = (
        f"TENDERGUARD_DOMAIN={domain}\nTENDERGUARD_TLS_EMAIL={email}\n"
        f"TENDERGUARD_API_KEY='{secrets.token_urlsafe(48)}'\n"
        f"TENDERGUARD_DASHBOARD_PASSWORD='{password}'\n"
        "TENDERGUARD_OLLAMA_MODEL=qwen3:1.7b\n"
        "TENDERGUARD_MAX_PDF_MB=10\nTENDERGUARD_MAX_PDF_PAGES=80\n"
    )
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as target:
        target.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name(".env"))
    args = parser.parse_args()
    password = getpass.getpass("Private dashboard password (16+ characters): ")
    if password != getpass.getpass("Confirm password: "):
        parser.error("Passwords did not match; nothing was written.")
    write_configuration(args.output, args.domain, args.email, password)
    print("Private cloud configuration created. Credentials were not displayed.")


if __name__ == "__main__":
    main()
