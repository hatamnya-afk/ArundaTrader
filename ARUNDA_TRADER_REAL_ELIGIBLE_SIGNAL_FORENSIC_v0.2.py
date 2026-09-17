from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

JSON_GLOB = "*.json"

ORDER_INTENT_KEYS = {
    "order_intents",
    "order_intent",
    "order_intent_path",
    "orders",
}


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (
        json.JSONDecodeError,
        OSError,
        UnicodeDecodeError,
    ):
        return None


def walk(
    obj: Any,
    path: str = "$",
):
    yield path, obj

    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from walk(
                value,
                f"{path}.{key}",
            )

    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from walk(
                value,
                f"{path}[{index}]",
            )


def is_signal_like(
    obj: Any,
) -> bool:

    if not isinstance(obj, dict):
        return False

    keys = {
        str(key).strip().lower()
        for key in obj.keys()
    }

    signal_markers = {
        "symbol",
        "entry_price",
        "signal",
        "signal_id",
        "signal_type",
        "side",
        "direction",
        "timestamp",
        "score",
    }

    return bool(
        keys.intersection(signal_markers)
    )


def artifact_eligible_count(
    obj: Any,
) -> int | None:

    candidates = []

    for path, value in walk(obj):

        if isinstance(value, bool):
            continue

        if not isinstance(value, int):
            continue

        key = (
            path.rsplit(".", 1)[-1]
            .replace("]", "")
            .split("[")[-1]
            .lower()
        )

        if key in {
            "eligible_rows",
            "eligible_signals",
            "eligible_count",
        }:
            if value >= 0:
                candidates.append(value)

    if not candidates:
        return None

    return max(candidates)


def collect_signal_candidates(
    obj: Any,
) -> list[tuple[str, dict[str, Any]]]:

    results = []

    for path, value in walk(obj):

        if not isinstance(value, dict):
            continue

        if is_signal_like(value):
            results.append(
                (
                    path,
                    value,
                )
            )

    return results


def inspect_signal(
    signal: dict[str, Any],
) -> dict[str, Any]:

    normalized = {
        str(key).strip().lower(): value
        for key, value in signal.items()
    }

    aliases = {
        "symbol": (
            "symbol",
            "ticker",
            "market",
        ),
        "entry_price": (
            "entry_price",
            "entry",
            "price",
        ),
        "side": (
            "side",
            "signal_side",
            "direction",
        ),
        "timestamp": (
            "timestamp",
            "signal_timestamp",
            "created_at",
            "time",
        ),
        "signal_id": (
            "signal_id",
            "id",
        ),
    }

    fields = {}

    for canonical, names in aliases.items():

        value = None

        for name in names:

            if name in normalized:
                value = normalized[name]
                break

        fields[canonical] = value

    missing = [
        key
        for key, value in fields.items()
        if value is None
    ]

    return {
        "fields": fields,
        "missing": missing,
        "complete": len(missing) == 0,
    }


def has_order_intent_evidence(
    obj: Any,
) -> bool:

    for path, value in walk(obj):

        key = (
            path.rsplit(".", 1)[-1]
            .replace("]", "")
            .split("[")[-1]
            .lower()
        )

        if key not in ORDER_INTENT_KEYS:
            continue

        if isinstance(value, bool):

            if value:
                return True

        elif isinstance(value, int):

            if value > 0:
                return True

        elif isinstance(value, list):

            if len(value) > 0:
                return True

        elif isinstance(value, dict):

            if len(value) > 0:
                return True

        elif value:

            return True

    return False


def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA TRADER — REAL ELIGIBLE SIGNAL FORENSIC v0.2"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )

    print(
        "MODE         : READ ONLY"
    )

    print(
        "DB ACCESS    : NONE"
    )

    print(
        "WRITE        : NONE"
    )

    print("=" * 100)

    if not PROJECT_ROOT.exists():

        print(
            "PROJECT ROOT STATUS : NOT FOUND"
        )

        return 1

    json_files = sorted(
        PROJECT_ROOT.glob(JSON_GLOB)
    )

    print(
        f"JSON ARTIFACTS SCANNED : "
        f"{len(json_files)}"
    )

    print("=" * 100)
    print(
        "A) ARTIFACT DISCOVERY"
    )
    print("=" * 100)

    eligible_artifacts = []

    signal_candidates = []

    order_intent_artifacts = []

    for path in json_files:

        data = load_json(path)

        if data is None:
            continue

        eligible_count = (
            artifact_eligible_count(
                data
            )
        )

        if (
            eligible_count is not None
            and eligible_count > 0
        ):

            eligible_artifacts.append(
                (
                    path,
                    eligible_count,
                )
            )

        candidates = (
            collect_signal_candidates(
                data
            )
        )

        for signal_path, signal in candidates:

            signal_candidates.append(
                (
                    path,
                    signal_path,
                    signal,
                )
            )

        if has_order_intent_evidence(
            data
        ):

            order_intent_artifacts.append(
                path
            )

    print(
        f"ARTIFACTS WITH eligible_count > 0 : "
        f"{len(eligible_artifacts)}"
    )

    print(
        f"SIGNAL-LIKE OBJECTS FOUND          : "
        f"{len(signal_candidates)}"
    )

    print(
        f"ARTIFACTS WITH ORDER-INTENT EVIDENCE : "
        f"{len(order_intent_artifacts)}"
    )

    print("=" * 100)
    print(
        "B) REAL ELIGIBLE SIGNAL"
    )
    print("=" * 100)

    if eligible_artifacts:

        for path, count in eligible_artifacts:

            print(
                f"ELIGIBLE ARTIFACT : {path}"
            )

            print(
                f"ELIGIBLE COUNT    : {count}"
            )

    else:

        print(
            "NO ARTIFACT WITH "
            "eligible_rows/eligible_signals > 0 FOUND."
        )

    print("=" * 100)
    print(
        "C) SIGNAL PATH FORENSIC"
    )
    print("=" * 100)

    if signal_candidates:

        for (
            artifact_path,
            signal_path,
            signal,
        ) in signal_candidates:

            inspection = inspect_signal(
                signal
            )

            print(
                f"ARTIFACT : {artifact_path}"
            )

            print(
                f"PATH     : {signal_path}"
            )

            print(
                f"COMPLETE : "
                f"{inspection['complete']}"
            )

            print(
                f"MISSING  : "
                f"{inspection['missing']}"
            )

            print(
                f"FIELDS   : "
                f"{inspection['fields']}"
            )

            print("-" * 100)

    else:

        print(
            "NO SIGNAL-LIKE OBJECT FOUND."
        )

    print("=" * 100)
    print(
        "D) ORDER-INTENT GENERATION EVIDENCE"
    )
    print("=" * 100)

    if order_intent_artifacts:

        for path in order_intent_artifacts:

            print(
                f"ORDER-INTENT EVIDENCE : {path}"
            )

    else:

        print(
            "NO POSITIVE ORDER-INTENT EVIDENCE FOUND."
        )

    print("=" * 100)
    print(
        "E) FINAL FORENSIC DECISION"
    )
    print("=" * 100)

    real_eligible_exists = (
        len(eligible_artifacts) > 0
    )

    complete_signal_exists = any(
        inspect_signal(signal)[
            "complete"
        ]
        for (
            _artifact_path,
            _signal_path,
            signal,
        ) in signal_candidates
    )

    generation_evidence_exists = (
        len(order_intent_artifacts) > 0
    )

    if not real_eligible_exists:

        verdict = (
            "BLOCKED_NO_ELIGIBLE_FIXTURE"
        )

        reason = (
            "No real eligible signal exists "
            "in the scanned project artifacts."
        )

    elif not complete_signal_exists:

        verdict = (
            "BLOCKED_ELIGIBLE_SIGNAL_CONTRACT"
        )

        reason = (
            "Eligible signal evidence exists, "
            "but no complete signal object was found "
            "with the required fields."
        )

    elif generation_evidence_exists:

        verdict = (
            "ELIGIBLE_SIGNAL_ALREADY_ENTERED_ORDER_INTENT_PATH"
        )

        reason = (
            "A real eligible signal exists and "
            "order-intent generation evidence was found."
        )

    else:

        verdict = (
            "READY_FOR_REAL_ELIGIBLE_SIGNAL_ORDER_INTENT_TRACE"
        )

        reason = (
            "A real eligible signal exists, "
            "its required fields are complete, "
            "and no prior order-intent generation "
            "evidence was found."
        )

    print(
        f"REAL ELIGIBLE SIGNAL : "
        f"{real_eligible_exists}"
    )

    print(
        f"COMPLETE SIGNAL       : "
        f"{complete_signal_exists}"
    )

    print(
        f"ORDER-INTENT EVIDENCE : "
        f"{generation_evidence_exists}"
    )

    print(
        f"VERDICT               : "
        f"{verdict}"
    )

    print(
        f"REASON                : "
        f"{reason}"
    )

    print("=" * 100)
    print(
        "SAFETY ASSERTION"
    )
    print("=" * 100)

    print(
        "DATABASE READ         : False"
    )

    print(
        "DATABASE WRITE        : False"
    )

    print(
        "JSON WRITE            : False"
    )

    print(
        "ARTIFACT MUTATION     : False"
    )

    print(
        "ORDER CREATION        : False"
    )

    print(
        "ORDER SUBMISSION      : False"
    )

    print(
        "NETWORK ACCESS        : False"
    )

    print("=" * 100)
    print(
        "END — READ ONLY FORENSIC"
    )
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())