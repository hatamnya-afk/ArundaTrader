"""Fail-closed startup preflight for the durable standing-mandate journal.

Read-only: never creates the journal, activates/revokes a mandate, calls a
provider, submits an order, or writes the trading database.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from standing_mandate_lifecycle_store_v0_1 import require_active_mandate

JOURNAL_PATH_ENV = "ARUNDA_MANDATE_LIFECYCLE_PATH"


def verify_mandate_service_configuration(
    *,
    expected_mandate_id: str,
    journal_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    raw_path = str(journal_path) if journal_path is not None else os.environ.get(JOURNAL_PATH_ENV)
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("MANDATE_LIFECYCLE_STORE_PATH_REQUIRED")

    target = Path(raw_path).expanduser()
    if not target.is_absolute():
        raise ValueError("MANDATE_LIFECYCLE_STORE_PATH_MUST_BE_ABSOLUTE")
    if target.is_symlink():
        raise ValueError("MANDATE_LIFECYCLE_STORE_PATH_SYMLINK_FORBIDDEN")
    if not target.exists():
        raise ValueError("MANDATE_LIFECYCLE_STORE_MISSING")
    if not target.is_file():
        raise ValueError("MANDATE_LIFECYCLE_STORE_NOT_FILE")

    resolved = target.resolve(strict=True)
    events = require_active_mandate(
        resolved,
        expected_mandate_id=expected_mandate_id,
    )
    return {
        "status": "PASS",
        "journal_path": str(resolved),
        "active_mandate_id": expected_mandate_id,
        "lifecycle_event_count": len(events),
        "provider_calls": 0,
        "database_writes": 0,
        "journal_mutated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mandate-id", required=True, help="Expected active mandate ID from the validated management record")
    args = parser.parse_args()
    try:
        result = verify_mandate_service_configuration(
            expected_mandate_id=args.mandate_id,
        )
    except (OSError, ValueError) as exc:
        print(f"MANDATE_SERVICE_PREFLIGHT=BLOCKED reason={exc}")
        return 2
    print(
        "MANDATE_SERVICE_PREFLIGHT=PASS "
        f"mandate_id={result['active_mandate_id']} "
        f"lifecycle_event_count={result['lifecycle_event_count']} "
        "provider_calls=0 database_writes=0 journal_mutated=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["JOURNAL_PATH_ENV", "verify_mandate_service_configuration"]
