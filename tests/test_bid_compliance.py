import json
from copy import deepcopy

import pytest

from app.agent import ollama_client
from mcp_servers.procurement.tools import check_bid_compliance
from mcp_servers.procurement.tools.check_bid_compliance import (
    check_bid_compliance_record,
)


def test_compliant_bid_passes():
    result = check_bid_compliance_record(
        "TG-DEMO-001",
        "BID-ALPHA-001",
    )

    assert result["status"] == "COMPLIANT"
    assert result["summary"]["failed_checks"] == 0
    assert result["summary"] == {"total_checks": 4, "passed_checks": 4, "failed_checks": 0}
    assert result["supplier"] == "Alpha Technologies Ltd"

    for check in result["checks"]:
        assert check["sources"]


def test_non_compliant_bid_is_flagged():
    result = check_bid_compliance_record(
        "TG-DEMO-001",
        "BID-BETA-001",
    )

    assert result["status"] == "NON_COMPLIANT"
    assert result["summary"] == {"total_checks": 4, "passed_checks": 2, "failed_checks": 2}

    failed_criteria = {check["criterion"] for check in result["checks"] if not check["passed"]}

    assert failed_criteria == {"TAX_CLEARANCE", "LOCAL_REGISTRATION"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("bid_id", "expected_priority"),
    [("BID-ALPHA-001", "STANDARD_REVIEW"), ("BID-BETA-001", "ATTENTION_REQUIRED")],
)
async def test_submission_timestamp_cannot_change_compliance_or_priority(
    monkeypatch, bid_id, expected_priority
):
    original_bid, source = check_bid_compliance._load_bid(bid_id)
    baseline = check_bid_compliance_record("TG-DEMO-001", bid_id)
    prompts = []

    async def fake_chat_structured(**kwargs):
        prompts.append(kwargs["user_prompt"])
        return json.dumps(
            {
                "review_priority": "STANDARD_REVIEW",
                "summary": "Mandatory evidence reviewed.",
                "reasons": [],
            }
        )

    monkeypatch.setattr(ollama_client, "_chat_structured", fake_chat_structured)
    for timestamp in ["2026-10-09T11:30:00+03:00", "2027-01-01T12:00:00+03:00", "invalid", None]:
        bid = deepcopy(original_bid)
        bid["submitted_at"] = timestamp
        monkeypatch.setattr(check_bid_compliance, "_load_bid", lambda _, bid=bid: (bid, source))
        compliance = check_bid_compliance_record("TG-DEMO-001", bid_id)
        assert compliance == baseline
        result = await ollama_client.synthesize_procurement_evidence(
            compliance, {"risk_level": "NORMAL_RANGE"}, {"risk_level": "LOW"}
        )
        assert result.review_priority == expected_priority
        assert result.human_committee_required is True
        assert result.final_award_decision is None
    assert all(prompt == prompts[0] for prompt in prompts)
