import io
import json
from urllib.error import HTTPError

import pytest

from deploy.validation import public_demo


@pytest.mark.parametrize(
    "origin",
    [
        "http://demo.trycloudflare.com",
        "https://password@demo.trycloudflare.com",
        "https://demo.trycloudflare.com/private",
        "https://other.test",
    ],
)
def test_external_probe_rejects_private_or_insecure_targets(origin):
    with pytest.raises(ValueError):
        public_demo.public_origin(origin)


def test_external_probe_checks_tls_dashboard_health_and_denied_report_access(monkeypatch):
    requests = []

    def respond(url, timeout):
        requests.append(url)
        if url.endswith("/api/browser/reports"):
            raise HTTPError(url, 401, "Unauthorized", {}, None)
        body = (
            json.dumps({"service": "tenderguard-africa"})
            if url.endswith("health")
            else "TenderGuard Africa"
        )
        response = io.BytesIO(body.encode())
        response.status = 200
        return response

    monkeypatch.setattr(public_demo, "urlopen", respond)
    result = public_demo.probe("https://synthetic.trycloudflare.com")
    assert result == {
        "public_https_dashboard": 200,
        "public_https_backend": 200,
        "unauthenticated_reports": 401,
        "credentials_sent": False,
    }
    assert len(requests) == 3
