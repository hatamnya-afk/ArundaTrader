from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

POLL_SECONDS = 2.0

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES",
}

EXCLUDED_FILE_MARKERS = (
    "FORENSIC",
    "AUDIT",
    "DIAGNOSTIC",
    "REPAIR",
    "WATCHER",
    "HEALTH",
    "TRACE",
    "VERIFICATION",
    "PREFLIGHT",
)

IDENTITY_KEYS = (
    "signal_id",
    "signal_identity",
    "signal_uuid",
    "signal_key",
    "signal_hash",
    "id",
)

SIGNAL_KEYS = (
    "signal",
    "signals",
    "eligible_signal",
    "eligible_signals",
    "fusion_signal",
    "fusion_signals",
)

SOURCE_KEYS = (
    "source",
    "producer",
    "producer_source",
    "artifact",
    "artifact_path",
    "snapshot_id",
    "run_id",
    "timestamp",
    "created_at",
    "generated_at",
)


def is_excluded_path(path: Path) -> bool:
    return any(
        part in EXCLUDED_DIRS
        for part in path.parts
    )


def is_excluded_file(path: Path) -> bool:
    upper = path.name.upper()

    return any(
        marker in upper
        for marker in EXCLUDED_FILE_MARKERS
    )


def discover_json_files() -> list[Path]:
    result = []

    for path in PROJECT_ROOT.rglob("*.json"):

        if is_excluded_path(path):
            continue

        if is_excluded_file(path):
            continue

        try:
            if path.is_file():
                result.append(path)
        except OSError:
            continue

    return sorted(result)


def file_fingerprint(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()

        return (
            int(stat.st_mtime_ns),
            int(stat.st_size),
        )

    except OSError:
        return (0, 0)


def load_json(
    path: Path,
) -> tuple[Any | None, str | None]:

    try:

        raw = path.read_text(
            encoding="utf-8-sig"
        )

        return (
            json.loads(raw),
            None,
        )

    except Exception as exc:

        return (
            None,
            str(exc),
        )


def scalar_identity(
    obj: dict[str, Any],
) -> str | None:

    for key in IDENTITY_KEYS:

        value = obj.get(key)

        if value is None:
            continue

        if isinstance(
            value,
            (
                str,
                int,
                float,
            ),
        ):

            text = str(value).strip()

            if text:
                return text

    return None


def contains_signal_identity(
    obj: dict[str, Any],
) -> bool:

    identity = scalar_identity(obj)

    if identity:
        return True

    for key in SIGNAL_KEYS:

        value = obj.get(key)

        if isinstance(value, dict):

            if scalar_identity(value):
                return True

        elif isinstance(value, list):

            for item in value:

                if isinstance(
                    item,
                    dict,
                ):

                    if scalar_identity(item):
                        return True

    return False


def is_eligible_value(
    value: Any,
) -> bool:

    if value is True:
        return True

    if isinstance(value, str):
        return value.strip().lower() == "true"

    if isinstance(value, int):
        return value == 1

    return False


def is_real_eligible_signal(
    obj: dict[str, Any],
) -> bool:

    if not is_eligible_value(
        obj.get("eligible")
    ):
        return False

    if not contains_signal_identity(obj):
        return False

    signal_context = False

    keys_lower = {
        str(key).lower()
        for key in obj.keys()
    }

    if any(
        key in keys_lower
        for key in SIGNAL_KEYS
    ):
        signal_context = True

    identity = scalar_identity(obj)

    if identity and any(
        token in " ".join(keys_lower)
        for token in (
            "signal",
            "fusion",
        )
    ):
        signal_context = True

    return signal_context


def extract_signal_candidates(
    value: Any,
    path: str = "$",
) -> list[tuple[str, dict[str, Any]]]:

    found: list[
        tuple[str, dict[str, Any]]
    ] = []

    if isinstance(value, dict):

        if is_real_eligible_signal(value):

            found.append(
                (
                    path,
                    value.copy(),
                )
            )

        for key, child in value.items():

            child_path = (
                f"{path}.{key}"
            )

            found.extend(
                extract_signal_candidates(
                    child,
                    child_path,
                )
            )

    elif isinstance(value, list):

        for index, child in enumerate(value):

            child_path = (
                f"{path}[{index}]"
            )

            found.extend(
                extract_signal_candidates(
                    child,
                    child_path,
                )
            )

    return found


def extract_provenance(
    obj: dict[str, Any],
) -> dict[str, Any]:

    result = {}

    for key in SOURCE_KEYS:

        if key in obj:

            result[key] = obj[key]

    identity = scalar_identity(obj)

    if identity is not None:

        result["resolved_identity"] = identity

    return result


def scan_file(
    path: Path,
) -> tuple[
    int,
    list[dict[str, Any]],
    str | None,
]:

    payload, error = load_json(path)

    if error:

        return (
            0,
            [],
            error,
        )

    candidates = extract_signal_candidates(
        payload
    )

    results = []

    for object_path, obj in candidates:

        results.append(
            {
                "artifact": str(path),
                "object_path": object_path,
                "identity": scalar_identity(obj),
                "eligible": obj.get("eligible"),
                "provenance": extract_provenance(obj),
                "object": obj,
            }
        )

    return (
        count_objects(payload),
        results,
        None,
    )


def count_objects(
    value: Any,
) -> int:

    count = 0

    if isinstance(value, dict):

        count += 1

        for child in value.values():
            count += count_objects(child)

    elif isinstance(value, list):

        for child in value:
            count += count_objects(child)

    return count


def newest_artifact(
    files: list[Path],
) -> tuple[Path | None, float]:

    newest: Path | None = None
    newest_time = 0.0

    for path in files:

        try:

            mtime = path.stat().st_mtime

            if mtime > newest_time:

                newest = path
                newest_time = mtime

        except OSError:
            continue

    return (
        newest,
        newest_time,
    )


def print_signal(
    signal: dict[str, Any],
) -> None:

    print()
    print("=" * 100)
    print(
        "REAL ELIGIBLE SIGNAL CAPTURED"
    )
    print("=" * 100)

    print(
        f"ARTIFACT       : "
        f"{signal['artifact']}"
    )

    print(
        f"OBJECT PATH    : "
        f"{signal['object_path']}"
    )

    print(
        f"SIGNAL IDENTITY: "
        f"{signal['identity']}"
    )

    print(
        f"ELIGIBLE       : "
        f"{signal['eligible']}"
    )

    print(
        "PROVENANCE:"
    )

    for key, value in signal[
        "provenance"
    ].items():

        print(
            f"  {key} : {value}"
        )

    print()
    print(
        "RAW SIGNAL OBJECT:"
    )

    print(
        json.dumps(
            signal["object"],
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    print("=" * 100)
    print(
        "CAPTURE STATUS : REAL_ELIGIBLE_SIGNAL_FOUND"
    )
    print("=" * 100)


def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA TRADER — FIRST REAL RUNTIME ELIGIBLE SIGNAL CAPTURE v0.1"
    )
    print("=" * 100)

    print(
        f"PROJECT ROOT       : {PROJECT_ROOT}"
    )
    print(
        "MODE               : READ ONLY"
    )
    print(
        "PRODUCTION EXECUTION : NONE"
    )
    print(
        "DATABASE ACCESS    : NONE"
    )
    print(
        "DATABASE WRITE     : NONE"
    )
    print(
        "JSON WRITE         : NONE"
    )
    print(
        "ARTIFACT CREATION  : NONE"
    )
    print(
        "NETWORK ACCESS     : NONE"
    )
    print(
        f"POLL SECONDS       : {POLL_SECONDS}"
    )

    print("=" * 100)
    print(
        "CAPTURE CONTRACT"
    )
    print("=" * 100)

    print(
        "The watcher observes only JSON artifacts."
    )

    print(
        "It never executes the production producer."
    )

    print(
        "It never creates a synthetic signal."
    )

    print(
        "It stops immediately after the first"
    )

    print(
        "REAL eligible=True signal with resolvable identity."
    )

    print("=" * 100)
    print(
        "INITIAL SCAN"
    )
    print("=" * 100)

    fingerprints: dict[
        str,
        tuple[int, int],
    ] = {}

    scan_number = 0

    while True:

        scan_number += 1

        files = discover_json_files()

        changed_files = []

        current_fingerprints = {}

        for path in files:

            fp = file_fingerprint(path)

            current_fingerprints[
                str(path)
            ] = fp

            if (
                str(path)
                not in fingerprints
            ):

                changed_files.append(path)

            elif (
                fingerprints[str(path)]
                != fp
            ):

                changed_files.append(path)

        fingerprints = current_fingerprints

        total_objects = 0
        parse_failures = 0
        eligible_count = 0

        captured_signal = None

        for path in files:

            object_count, signals, error = (
                scan_file(path)
            )

            total_objects += object_count

            if error:

                parse_failures += 1

                continue

            if signals:

                eligible_count += len(
                    signals
                )

                if captured_signal is None:

                    captured_signal = (
                        signals[0]
                    )

        newest, newest_time = (
            newest_artifact(files)
        )

        timestamp = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        print()
        print("-" * 100)
        print(
            f"HEARTBEAT : {timestamp}"
        )

        print(
            f"SCAN      : {scan_number}"
        )

        print(
            f"JSON ARTIFACTS : {len(files)}"
        )

        print(
            f"ARTIFACT CHANGES : "
            f"{len(changed_files)}"
        )

        if changed_files:

            print(
                "CHANGED ARTIFACTS:"
            )

            for path in changed_files:

                print(
                    f"  {path}"
                )

        if newest is not None:

            newest_time_text = (
                time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(
                        newest_time
                    ),
                )
            )

            print(
                f"NEWEST ARTIFACT : {newest}"
            )

            print(
                f"NEWEST ARTIFACT TIME : "
                f"{newest_time_text}"
            )

        print(
            f"SIGNAL OBJECTS SCANNED : "
            f"{total_objects}"
        )

        print(
            f"PARSE FAILURES : "
            f"{parse_failures}"
        )

        print(
            f"ELIGIBLE DETECTIONS : "
            f"{eligible_count}"
        )

        if captured_signal is not None:

            print_signal(
                captured_signal
            )

            print()
            print(
                "NEXT STAGE:"
            )

            print(
                "STOP WATCHER."
            )

            print(
                "Do NOT execute generator automatically."
            )

            print(
                "Use the captured identity/artifact/object"
            )

            print(
                "for the next forensic chain."
            )

            print("=" * 100)
            print(
                "SAFETY ASSERTION"
            )
            print("=" * 100)

            print(
                "PYTHON PRODUCTION EXECUTION : False"
            )
            print(
                "DATABASE READ              : False"
            )
            print(
                "DATABASE WRITE             : False"
            )
            print(
                "JSON WRITE                 : False"
            )
            print(
                "ARTIFACT CREATION          : False"
            )
            print(
                "ORDER CREATION             : False"
            )
            print(
                "ORDER SUBMISSION           : False"
            )
            print(
                "NETWORK ACCESS             : False"
            )
            print(
                "ARTIFACT MUTATION          : False"
            )

            return 0

        print(
            "WATCHER STATUS : "
            "WAIT_FOR_ELIGIBLE_SIGNAL"
        )

        time.sleep(
            POLL_SECONDS
        )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )