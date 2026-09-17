from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
}

MAX_SIGNAL_OBJECTS_TO_PRINT = 20


def print_section(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def safe_load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return None, str(exc)

    if not isinstance(data, dict):
        return None, "JSON root is not a dict."

    return data, None


def is_excluded(path: Path) -> bool:
    try:
        relative = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return True

    return any(
        part in EXCLUDED_DIRS
        for part in relative.parts
    )


def json_files() -> list[Path]:
    files: list[Path] = []

    for path in PROJECT_ROOT.rglob("*.json"):
        if is_excluded(path):
            continue

        if path.is_file():
            files.append(path)

    return sorted(files)


def looks_like_signal_object(obj: dict[str, Any]) -> bool:
    signal_keys = {
        "id",
        "signal_id",
        "row_id",
        "asset",
        "symbol",
        "direction",
        "eligible",
        "status",
        "confidence",
        "entry_price",
        "timestamp",
    }

    return len(
        signal_keys.intersection(obj.keys())
    ) >= 2


def signal_identity(obj: dict[str, Any]) -> dict[str, Any]:
    identity: dict[str, Any] = {}

    for key in (
        "id",
        "signal_id",
        "row_id",
        "asset",
        "symbol",
        "timestamp",
        "direction",
        "status",
        "eligible",
        "confidence",
        "entry_price",
    ):
        if key in obj:
            identity[key] = obj[key]

    return identity


def has_resolvable_identity(obj: dict[str, Any]) -> bool:
    identity_keys = (
        "id",
        "signal_id",
        "row_id",
    )

    for key in identity_keys:
        value = obj.get(key)

        if isinstance(value, (int, str)) and str(value).strip():
            return True

    return False


def walk_objects(
    obj: Any,
    path: str = "$",
):
    if isinstance(obj, dict):

        yield path, obj

        for key, value in obj.items():

            child_path = f"{path}.{key}"

            yield from walk_objects(
                value,
                child_path,
            )

    elif isinstance(obj, list):

        for index, item in enumerate(obj):

            child_path = (
                f"{path}[{index}]"
            )

            yield from walk_objects(
                item,
                child_path,
            )


def is_real_eligible_signal(
    obj: dict[str, Any],
) -> bool:

    eligible = obj.get("eligible")

    if eligible is not True:
        return False

    return has_resolvable_identity(obj)


def extract_eligible_signals(
    data: dict[str, Any],
) -> list[dict[str, Any]]:

    results: list[dict[str, Any]] = []

    for path, obj in walk_objects(data):

        if not is_real_eligible_signal(obj):
            continue

        results.append(
            {
                "path": path,
                "identity": signal_identity(obj),
                "object": obj,
            }
        )

    return results


def inspect_signal_completeness(
    obj: dict[str, Any],
) -> dict[str, Any]:

    required_groups = {
        "identity": (
            "id",
            "signal_id",
            "row_id",
        ),
        "asset": (
            "asset",
            "symbol",
        ),
        "direction": (
            "direction",
        ),
        "timestamp": (
            "timestamp",
        ),
        "entry_price": (
            "entry_price",
        ),
    }

    present: dict[str, Any] = {}
    missing: list[str] = []

    for group, keys in required_groups.items():

        found = False

        for key in keys:

            if key in obj and obj[key] is not None:

                present[group] = key
                found = True
                break

        if not found:
            missing.append(group)

    return {
        "complete_for_basic_generator_trace": (
            len(missing) == 0
        ),
        "present_groups": present,
        "missing_groups": missing,
    }


def find_order_intent_evidence(
    obj: Any,
    path: str = "$",
) -> list[dict[str, Any]]:

    evidence: list[dict[str, Any]] = []

    if isinstance(obj, dict):

        for key, value in obj.items():

            lowered = key.lower()

            child_path = (
                f"{path}.{key}"
            )

            if lowered in {
                "order_intent",
                "order_intents",
                "validated_intents",
                "invalid_intents",
            }:

                evidence.append(
                    {
                        "path": child_path,
                        "key": key,
                        "value": value,
                    }
                )

            evidence.extend(
                find_order_intent_evidence(
                    value,
                    child_path,
                )
            )

    elif isinstance(obj, list):

        for index, item in enumerate(obj):

            evidence.extend(
                find_order_intent_evidence(
                    item,
                    f"{path}[{index}]",
                )
            )

    return evidence


def find_id_references(
    obj: Any,
    target_id: Any,
    path: str = "$",
) -> list[str]:

    references: list[str] = []

    if isinstance(obj, dict):

        for key, value in obj.items():

            child_path = (
                f"{path}.{key}"
            )

            if value == target_id:
                references.append(
                    child_path
                )

            references.extend(
                find_id_references(
                    value,
                    target_id,
                    child_path,
                )
            )

    elif isinstance(obj, list):

        for index, item in enumerate(obj):

            child_path = (
                f"{path}[{index}]"
            )

            if item == target_id:
                references.append(
                    child_path
                )

            references.extend(
                find_id_references(
                    item,
                    target_id,
                    child_path,
                )
            )

    return references


def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA TRADER — FIRST REAL ELIGIBLE SIGNAL "
        "CHAIN FORENSIC v0.1"
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
        "PYTHON EXECUTION : NONE"
    )

    print(
        "WRITE        : NONE"
    )

    print(
        "ARTIFACT CREATION : NONE"
    )

    print("=" * 100)

    if not PROJECT_ROOT.exists():

        print(
            "ERROR: PROJECT ROOT NOT FOUND"
        )

        return 1

    files = json_files()

    print_section(
        "A) ARTIFACT DISCOVERY"
    )

    print(
        f"JSON ARTIFACTS DISCOVERED : "
        f"{len(files)}"
    )

    eligible_records: list[
        dict[str, Any]
    ] = []

    parse_failures: list[
        dict[str, str]
    ] = []

    signal_like_count = 0

    for path in files:

        data, error = safe_load_json(
            path
        )

        if error is not None:

            parse_failures.append(
                {
                    "path": str(path),
                    "error": error,
                }
            )

            continue

        if data is None:
            continue

        for _, obj in walk_objects(data):

            if (
                isinstance(obj, dict)
                and looks_like_signal_object(obj)
            ):
                signal_like_count += 1

        found = extract_eligible_signals(
            data
        )

        for record in found:

            record["artifact"] = str(
                path
            )

            eligible_records.append(
                record
            )

    print(
        f"SIGNAL-LIKE OBJECTS : "
        f"{signal_like_count}"
    )

    print(
        f"JSON PARSE FAILURES : "
        f"{len(parse_failures)}"
    )

    if parse_failures:

        for failure in parse_failures:

            print(
                "\nPARSE FAILURE : "
                f"{failure['path']}"
            )

            print(
                f"ERROR : "
                f"{failure['error']}"
            )

    print_section(
        "B) REAL ELIGIBLE SIGNAL DISCOVERY"
    )

    print(
        f"REAL ELIGIBLE SIGNAL OBJECTS : "
        f"{len(eligible_records)}"
    )

    if not eligible_records:

        print()
        print(
            "REAL ELIGIBLE SIGNAL : False"
        )

        print(
            "VERDICT : WAIT_FOR_ELIGIBLE_SIGNAL"
        )

        print(
            "REASON  : No artifact currently "
            "contains an object with eligible=True "
            "and a resolvable signal identity."
        )

        print_section(
            "C) SAFETY ASSERTION"
        )

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
            "END — READ ONLY"
        )
        print("=" * 100)

        return 0

    print(
        "REAL ELIGIBLE SIGNAL : True"
    )

    print_section(
        "D) REAL ELIGIBLE SIGNALS FOUND"
    )

    for index, record in enumerate(
        eligible_records[
            :MAX_SIGNAL_OBJECTS_TO_PRINT
        ],
        start=1,
    ):

        print(
            f"\nREAL ELIGIBLE SIGNAL #{index}"
        )

        print(
            f"ARTIFACT : "
            f"{record['artifact']}"
        )

        print(
            f"PATH     : "
            f"{record['path']}"
        )

        print(
            "IDENTITY : "
            f"{record['identity']}"
        )

        print(
            "OBJECT   : "
            f"{record['object']}"
        )

    print_section(
        "E) FIRST REAL ELIGIBLE SIGNAL TARGET"
    )

    target = eligible_records[0]

    target_object = target[
        "object"
    ]

    target_id = None

    for key in (
        "id",
        "signal_id",
        "row_id",
    ):

        if key in target_object:

            target_id = target_object[key]
            break

    print(
        f"TARGET ARTIFACT : "
        f"{target['artifact']}"
    )

    print(
        f"TARGET PATH     : "
        f"{target['path']}"
    )

    print(
        f"TARGET ID       : "
        f"{target_id}"
    )

    print(
        f"TARGET IDENTITY  : "
        f"{target['identity']}"
    )

    print_section(
        "F) SIGNAL → GENERATOR INPUT READINESS"
    )

    completeness = inspect_signal_completeness(
        target_object
    )

    print(
        "COMPLETE FOR BASIC GENERATOR TRACE : "
        f"{completeness['complete_for_basic_generator_trace']}"
    )

    print(
        "PRESENT GROUPS : "
        f"{completeness['present_groups']}"
    )

    print(
        "MISSING GROUPS : "
        f"{completeness['missing_groups']}"
    )

    print_section(
        "G) CROSS-ARTIFACT ID TRACE"
    )

    if target_id is None:

        print(
            "TARGET ID : UNRESOLVED"
        )

        print(
            "ID TRACE : NOT POSSIBLE"
        )

    else:

        id_reference_count = 0

        for path in files:

            data, error = safe_load_json(
                path
            )

            if error is not None or data is None:
                continue

            references = find_id_references(
                data,
                target_id,
            )

            if not references:
                continue

            id_reference_count += len(
                references
            )

            print(
                f"\nARTIFACT : {path}"
            )

            print(
                f"ID REFERENCES : "
                f"{len(references)}"
            )

            for reference in references:
                print(
                    f"  {reference}"
                )

        print(
            f"\nTOTAL ID REFERENCES : "
            f"{id_reference_count}"
        )

    print_section(
        "H) ORDER-INTENT EVIDENCE TRACE"
    )

    order_intent_evidence_total = 0

    for path in files:

        data, error = safe_load_json(
            path
        )

        if error is not None or data is None:
            continue

        evidence = find_order_intent_evidence(
            data
        )

        if not evidence:
            continue

        for item in evidence:

            order_intent_evidence_total += 1

            print(
                f"\nARTIFACT : {path}"
            )

            print(
                f"PATH     : "
                f"{item['path']}"
            )

            print(
                f"KEY      : "
                f"{item['key']}"
            )

            print(
                f"VALUE    : "
                f"{item['value']}"
            )

    print(
        f"\nORDER-INTENT EVIDENCE NODES : "
        f"{order_intent_evidence_total}"
    )

    print_section(
        "I) FINAL FORENSIC DECISION"
    )

    if completeness[
        "complete_for_basic_generator_trace"
    ]:

        verdict = (
            "REAL_ELIGIBLE_SIGNAL_READY_FOR_EXACT_CHAIN_TRACE"
        )

        reason = (
            "A real eligible signal with resolvable "
            "identity was found and contains the "
            "basic fields required to begin an exact "
            "producer-to-generator forensic trace."
        )

    else:

        verdict = (
            "REAL_ELIGIBLE_SIGNAL_FOUND_INPUT_INCOMPLETE"
        )

        reason = (
            "A real eligible signal exists, but its "
            "artifact representation is missing one "
            "or more basic fields required for the "
            "generator-input trace."
        )

    print(
        f"REAL ELIGIBLE SIGNAL : True"
    )

    print(
        f"TARGET ID            : {target_id}"
    )

    print(
        f"COMPLETE SIGNAL      : "
        f"{completeness['complete_for_basic_generator_trace']}"
    )

    print(
        f"ORDER-INTENT EVIDENCE : "
        f"{order_intent_evidence_total > 0}"
    )

    print(
        f"VERDICT              : {verdict}"
    )

    print(
        f"REASON               : {reason}"
    )

    print_section(
        "J) IMPORTANT LIMITATION"
    )

    print(
        "This forensic is READ-ONLY artifact inspection."
    )

    print(
        "It does NOT execute production Python."
    )

    print(
        "It does NOT access the database."
    )

    print(
        "It does NOT generate an eligible signal."
    )

    print(
        "It does NOT generate an order intent."
    )

    print(
        "It does NOT validate an order intent."
    )

    print(
        "It does NOT open the execution gate."
    )

    print(
        "It does NOT modify any artifact."
    )

    print_section(
        "K) SAFETY ASSERTION"
    )

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
        "END — READ ONLY FIRST REAL ELIGIBLE SIGNAL FORENSIC"
    )
    print("=" * 100)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())