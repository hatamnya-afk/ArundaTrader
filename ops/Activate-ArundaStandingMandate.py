"""Explicitly persist the already-authorized management phase-entry decision.

The JSON input must be derived from the canonical management decision record.
Default mode validates and reports only. Journal mutation requires the explicit
--confirm-activate flag. No provider/database calls or order submission occur.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from collections.abc import Mapping

from management_execution_authorization_v0_1 import evaluate_management_phase_entry
from standing_mandate_lifecycle_store_v0_1 import record_management_phase_entry
from standing_mandate_service_preflight_v0_1 import JOURNAL_PATH_ENV, verify_mandate_service_configuration


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision-json", required=True, help="Protected JSON containing the management_observation from the canonical decision record")
    parser.add_argument("--confirm-activate", action="store_true", help="Append the validated ACTIVATE event to the durable journal")
    args = parser.parse_args()

    source = Path(args.decision_json)
    if not source.is_absolute():
        parser.error("--decision-json must be an absolute path")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("MANAGEMENT_DECISION_FILE_INVALID")
        observation = payload.get("management_observation")
        if not isinstance(observation, Mapping):
            raise ValueError("MANAGEMENT_OBSERVATION_REQUIRED")
        validated = evaluate_management_phase_entry(observation)
        if validated.get("management_state") != "AUTHORIZED":
            raise ValueError("MANAGEMENT_PHASE_ENTRY_NOT_AUTHORIZED")
        if not args.confirm_activate:
            print(
                "MANDATE_ACTIVATION=VALIDATED_DRY_RUN "
                f"mandate_id={validated['mandate_id']} "
                f"journal_mutated=false"
            )
            return 0

        journal_path = os.environ.get(JOURNAL_PATH_ENV)
        if not journal_path or not journal_path.strip():
            raise ValueError("MANDATE_LIFECYCLE_STORE_PATH_REQUIRED")
        events = record_management_phase_entry(journal_path, validated)
        verify_mandate_service_configuration(
            expected_mandate_id=validated["mandate_id"],
            journal_path=journal_path,
        )
        print(
            "MANDATE_ACTIVATION=PASS "
            f"mandate_id={validated['mandate_id']} "
            f"lifecycle_event_count={len(events)} "
            "provider_calls=0 database_writes=0"
        )
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"MANDATE_ACTIVATION=BLOCKED reason={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
