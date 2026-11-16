"""Static safeguards against accidentally shipping backend credentials to the browser."""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SOURCE = PROJECT_ROOT / "frontend" / "src"


def test_frontend_source_contains_no_backend_secret_contracts():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(FRONTEND_SOURCE.rglob("*"))
        if path.is_file() and ".test." not in path.name and "test" not in path.parts
    )
    forbidden = [
        "TENDERGUARD_API_KEY",
        "X-TenderGuard-Key",
        "VITE_API_KEY",
        "VITE_TENDERGUARD_KEY",
    ]
    assert all(item not in source for item in forbidden)
    assert (
        re.search(
            r"localStorage\.(?:setItem|getItem)\([^)]*password",
            source,
            re.IGNORECASE,
        )
        is None
    )


def test_dashboard_calls_only_the_session_protected_browser_api():
    api_source = (FRONTEND_SOURCE / "lib" / "api.ts").read_text(encoding="utf-8")
    paths = re.findall(r'"(/api/[^"?]+)', api_source)
    assert paths
    assert all(path.startswith("/api/browser/") for path in paths)
