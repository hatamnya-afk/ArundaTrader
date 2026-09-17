from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_FILES = [
    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_ELIGIBLE_SIGNAL_REPLAY_VERIFICATION_REPORT.json",

    PROJECT_ROOT
    / "ARUNDA_TRADER_LIVE_SIGNAL_EXECUTION_DRY_RUN_REPORT.json",
]


ORDER_INTENT_KEYS = {
    "order_intents",
    "order_intent",
    "orders",
    "order_intent_path",
}

SIGNAL_KEYS = {
    "signal_id",
    "symbol",
    "ticker",
    "entry_price",
    "side",
    "direction",
    "signal_type",
    "timestamp",
}

ELIGIBLE_KEYS = {
    "eligible_signal",
    "eligible_signals",
    "eligible_rows",
    "eligible_count",
}


def load_json(path: Path) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def walk(
    obj: Any,
    path: str = "$",
    parents: tuple[Any, ...] = (),
):
    yield path, obj, parents

    if isinstance(obj, dict):

        for key, value in obj.items():

            yield from walk(
                value,
                f"{path}.{key}",
                parents + (obj,),
            )

    elif isinstance(obj, list):

        for index, value in enumerate(obj):

            yield from walk(
                value,
                f"{path}[{index}]",
                parents + (obj,),
            )


def normalize_key(
    path: str,
) -> str:

    return (
        path
        .rsplit(".", 1)[-1]
        .replace("]", "")
        .split("[")[-1]
        .lower()
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

    return bool(
        keys.intersection(
            SIGNAL_KEYS
        )
    )


def is_positive_order_intent(
    value: Any,
) -> bool:

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value > 0

    if isinstance(value, float):
        return value > 0

    if isinstance(value, list):
        return len(value) > 0

    if isinstance(value, dict):
        return len(value) > 0

    if isinstance(value, str):
        return bool(value.strip())

    return False


def describe_value(
    value: Any,
) -> str:

    if isinstance(value, list):
        return (
            f"LIST(len={len(value)})"
        )

    if isinstance(value, dict):
        return (
            f"DICT(keys={list(value.keys())})"
        )

    return (
        f"{type(value).__name__}({value!r})"
    )


def inspect_file(
    path: Path,
) -> dict[str, Any]:

    result = {
        "path": str(path),
        "order_paths": [],
        "positive_order_paths": [],
        "signal_paths": [],
        "eligible_paths": [],
    }

    data = load_json(path)

    for (
        current_path,
        value,
        parents,
    ) in walk(data):

        key = normalize_key(
            current_path
        )

        if key in ORDER_INTENT_KEYS:

            result[
                "order_paths"
            ].append(
                (
                    current_path,
                    value,
                )
            )

            if is_positive_order_intent(
                value
            ):

                result[
                    "positive_order_paths"
                ].append(
                    (
                        current_path,
                        value,
                    )
                )

        if key in ELIGIBLE_KEYS:

            result[
                "eligible_paths"
            ].append(
                (
                    current_path,
                    value,
                )
            )

        if is_signal_like(value):

            result[
                "signal_paths"
            ].append(
                (
                    current_path,
                    value,
                )
            )

    return result


def find_nearest_signal_parent(
    path: str,
    signal_paths: list[
        tuple[str, dict[str, Any]]
    ],
) -> tuple[
    str,
    dict[str, Any],
] | None:

    candidates = []

    for signal_path, signal in signal_paths:

        if path.startswith(
            signal_path
        ):

            candidates.append(
                (
                    len(signal_path),
                    signal_path,
                    signal,
                )
            )

    if not candidates:
        return None

    candidates.sort(
        reverse=True
    )

    _length, signal_path, signal = (
        candidates[0]
    )

    return (
        signal_path,
        signal,
    )


def inspect_order_object(
    value: Any,
) -> dict[str, Any]:

    result = {
        "real_object": False,
        "object_type": type(value).__name__,
        "count": 0,
        "items": [],
    }

    if isinstance(value, list):

        result["count"] = len(value)

        if len(value) == 0:
            return result

        result["real_object"] = True

        for index, item in enumerate(
            value
        ):

            result["items"].append(
                {
                    "index": index,
                    "type": type(item).__name__,
                    "value": item,
                }
            )

        return result

    if isinstance(value, dict):

        result["count"] = 1

        if len(value) == 0:
            return result

        result["real_object"] = True

        result["items"].append(
            {
                "index": 0,
                "type": "dict",
                "value": value,
            }
        )

        return result

    if isinstance(value, int):

        result["count"] = value

        if value > 0:
            result["real_object"] = True

        return result

    if isinstance(value, str):

        if value.strip():
            result["real_object"] = True
            result["count"] = 1

        return result

    return result


def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA TRADER — ORDER-INTENT EVIDENCE FORENSIC v0.1"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT : {PROJECT_ROOT}"
    )

    print(
        "MODE         : READ ONLY"
    )

    print(
        "DATABASE     : NONE"
    )

    print(
        "WRITE        : NONE"
    )

    print("=" * 100)

    total_order_paths = 0
    total_positive_paths = 0
    total_signal_paths = 0

    file_results = []

    for path in TARGET_FILES:

        print("=" * 100)
        print(
            f"ARTIFACT : {path}"
        )
        print("=" * 100)

        if not path.exists():

            print(
                "STATUS : FILE NOT FOUND"
            )

            continue

        result = inspect_file(
            path
        )

        file_results.append(
            result
        )

        order_paths = result[
            "order_paths"
        ]

        positive_paths = result[
            "positive_order_paths"
        ]

        signal_paths = result[
            "signal_paths"
        ]

        eligible_paths = result[
            "eligible_paths"
        ]

        total_order_paths += len(
            order_paths
        )

        total_positive_paths += len(
            positive_paths
        )

        total_signal_paths += len(
            signal_paths
        )

        print(
            f"ORDER-INTENT PATHS FOUND : "
            f"{len(order_paths)}"
        )

        for path_value, value in (
            order_paths
        ):

            print(
                f"PATH   : {path_value}"
            )

            print(
                f"VALUE  : "
                f"{describe_value(value)}"
            )

            inspection = (
                inspect_order_object(
                    value
                )
            )

            print(
                f"REAL OBJECT : "
                f"{inspection['real_object']}"
            )

            print(
                f"COUNT       : "
                f"{inspection['count']}"
            )

        print("-" * 100)

        print(
            f"POSITIVE ORDER-INTENT PATHS : "
            f"{len(positive_paths)}"
        )

        for path_value, value in (
            positive_paths
        ):

            print(
                f"POSITIVE PATH : "
                f"{path_value}"
            )

            print(
                f"VALUE         : "
                f"{describe_value(value)}"
            )

            nearest_signal = (
                find_nearest_signal_parent(
                    path_value,
                    signal_paths,
                )
            )

            if nearest_signal is None:

                print(
                    "SIGNAL PARENT : NONE"
                )

            else:

                signal_path, signal = (
                    nearest_signal
                )

                print(
                    f"SIGNAL PARENT : "
                    f"{signal_path}"
                )

                print(
                    f"SIGNAL OBJECT : "
                    f"{signal}"
                )

        print("-" * 100)

        print(
            f"SIGNAL-LIKE OBJECTS : "
            f"{len(signal_paths)}"
        )

        for signal_path, signal in (
            signal_paths
        ):

            print(
                f"SIGNAL PATH : "
                f"{signal_path}"
            )

            print(
                f"SIGNAL      : "
                f"{signal}"
            )

        print("-" * 100)

        print(
            f"ELIGIBILITY PATHS : "
            f"{len(eligible_paths)}"
        )

        for eligible_path, value in (
            eligible_paths
        ):

            print(
                f"ELIGIBLE PATH : "
                f"{eligible_path}"
            )

            print(
                f"VALUE         : "
                f"{describe_value(value)}"
            )

    print("=" * 100)
    print(
        "FINAL FORENSIC DECISION"
    )
    print("=" * 100)

    real_order_intent = (
        total_positive_paths > 0
    )

    real_signal = (
        total_signal_paths > 0
    )

    if real_order_intent and real_signal:

        verdict = (
            "REAL_ORDER_INTENT_WITH_SIGNAL_EVIDENCE"
        )

        reason = (
            "Positive order-intent evidence "
            "and signal-like evidence coexist."
        )

    elif real_order_intent and not real_signal:

        verdict = (
            "ORDER_INTENT_WITHOUT_SIGNAL_EVIDENCE"
        )

        reason = (
            "Positive order-intent evidence exists, "
            "but no signal-like parent/object was found."
        )

    elif total_order_paths > 0:

        verdict = (
            "STRUCTURAL_ORDER_INTENT_ONLY"
        )

        reason = (
            "Order-intent fields exist, "
            "but no positive order-intent object "
            "was found."
        )

    else:

        verdict = (
            "NO_ORDER_INTENT_EVIDENCE"
        )

        reason = (
            "No order-intent field or object was found "
            "in the targeted artifacts."
        )

    print(
        f"ORDER-INTENT PATHS       : "
        f"{total_order_paths}"
    )

    print(
        f"POSITIVE ORDER-INTENTS   : "
        f"{total_positive_paths}"
    )

    print(
        f"SIGNAL-LIKE OBJECTS      : "
        f"{total_signal_paths}"
    )

    print(
        f"REAL ORDER-INTENT        : "
        f"{real_order_intent}"
    )

    print(
        f"REAL SIGNAL EVIDENCE     : "
        f"{real_signal}"
    )

    print(
        f"VERDICT                  : "
        f"{verdict}"
    )

    print(
        f"REASON                   : "
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