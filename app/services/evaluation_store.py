from collections import OrderedDict
from threading import Lock
from typing import Any

_MAX_EVALUATIONS = 50
_evaluations: OrderedDict[str, dict[str, Any]] = OrderedDict()
_lock = Lock()


def save_evaluation(evaluation: dict[str, Any]) -> None:
    evaluation_id = str(evaluation["evaluation_id"])
    with _lock:
        _evaluations[evaluation_id] = evaluation
        _evaluations.move_to_end(evaluation_id)
        while len(_evaluations) > _MAX_EVALUATIONS:
            _evaluations.popitem(last=False)


def list_evaluation_summaries() -> list[dict[str, Any]]:
    with _lock:
        records = list(reversed(_evaluations.values()))
    return [
        {
            "evaluation_id": item["evaluation_id"],
            "completed_at": item["completed_at"],
            "tender_id": item["tender_id"],
            "bid_id": item["bid_id"],
            "supplier": (item.get("compliance") or {}).get("supplier"),
            "status": item["status"],
            "review_priority": item["decision_support"]["review_priority"],
            "final_award_decision": None,
        }
        for item in records
    ]


def reset_evaluations_for_tests() -> None:
    with _lock:
        _evaluations.clear()
