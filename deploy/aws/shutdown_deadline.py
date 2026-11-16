"""Calculate the approved eight-hour stop deadline from EC2 IMDSv2 identity JSON."""

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from typing import Any


def shutdown_deadline(
    identity: dict[str, Any], expected_instance: str, *, now: datetime | None = None
) -> datetime:
    if identity.get("instanceId") != expected_instance:
        raise ValueError("EC2 identity does not match the approved dedicated instance.")
    launched = datetime.fromisoformat(identity["pendingTime"])
    if launched.utcoffset() is None:
        raise ValueError("EC2 launch time must include a timezone.")
    if launched > (now or datetime.now(UTC)) + timedelta(minutes=5):
        raise ValueError("EC2 launch time is unexpectedly in the future.")
    return (launched + timedelta(hours=8)).astimezone(UTC)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-id", required=True)
    args = parser.parse_args()
    deadline = shutdown_deadline(json.load(sys.stdin), args.instance_id)
    print(deadline.strftime("%Y-%m-%d %H:%M:%S UTC"))


if __name__ == "__main__":
    main()
