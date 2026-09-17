from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

POLL_SECONDS = 2.0

SIGNAL_KEYS = {
    "eligible",
    "signal_id",
    "row_id",
    "id",
    "asset",
    "symbol",
    "direction",
    "timestamp",
    "entry_price",
}


def safe_load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
        ) as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

        return None

    except Exception:
        return None


def discover_json_files() -> list[Path]:
    files: list[Path] = []

    for path in PROJECT_ROOT.rglob("*.json"):
        if not path.is_file():
            continue

        files.append(path)

    return sorted(files)


def file_signature(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()
        return (
            int(stat.st_mtime_ns),
            int(stat.st_size),
        )
    except OSError:
        return (
            0,
            0,
        )


def newest_artifact(
    files: list[Path],
) -> tuple[Path | None, float]:

    newest_path: Path | None = None
    newest_mtime = 0.0

    for path in files:

        try:
            mtime = path.stat().st_mtime

        except OSError:
            continue

        if mtime > newest_mtime:

            newest_mtime = mtime
            newest_path = path

    return (
        newest_path,
        newest_mtime,
    )


def is_signal_like(
    obj: dict[str, Any],
) -> bool:

    keys = {
        str(key)
        for key in obj.keys()
    }

    return bool(
        keys & SIGNAL_KEYS
    )


def has_resolvable_identity(
    obj: dict[str, Any],
) -> bool:

    identity_keys = (
        "signal_id",
        "row_id",
        "id",
    )

    for key in identity_keys:

        value = obj.get(key)

        if isinstance(
            value,
            int,
        ):
            return True

        if isinstance(
            value,
            str,
        ) and value.strip():

            return True

    asset = obj.get("asset")

    symbol = obj.get("symbol")

    if isinstance(
        asset,
        str,
    ) and asset.strip():

        return True

    if isinstance(
        symbol,
        str,
    ) and symbol.strip():

        return True

    return False


def scan_object(
    obj: Any,
) -> tuple[int, int, list[dict[str, Any]]]:

    signal_count = 0
    eligible_count = 0
    detections: list[dict[str, Any]] = []

    if isinstance(
        obj,
        dict,
    ):

        if is_signal_like(obj):

            signal_count += 1

            eligible = obj.get(
                "eligible"
            )

            if (
                eligible is True
                and has_resolvable_identity(obj)
            ):

                eligible_count += 1

                detections.append(
                    dict(obj)
                )

        for value in obj.values():

            child_signals, child_eligible, child_detections = scan_object(
                value
            )

            signal_count += child_signals
            eligible_count += child_eligible
            detections.extend(
                child_detections
            )

    elif isinstance(
        obj,
        list,
    ):

        for item in obj:

            child_signals, child_eligible, child_detections = scan_object(
                item
            )

            signal_count += child_signals
            eligible_count += child_eligible
            detections.extend(
                child_detections
            )

    return (
        signal_count,
        eligible_count,
        detections,
    )


def scan_files(
    files: list[Path],
) -> dict[str, Any]:

    signal_objects = 0
    eligible_detections = 0
    parse_failures = 0

    detected_paths: list[str] = []

    for path in files:

        data = safe_load_json(path)

        if data is None:

            parse_failures += 1
            continue

        signals, eligible, detections = scan_object(
            data
        )

        signal_objects += signals
        eligible_detections += eligible

        if detections:

            for detection in detections:

                detected_paths.append(
                    str(path)
                )

    return {
        "signal_objects": signal_objects,
        "eligible_detections": eligible_detections,
        "parse_failures": parse_failures,
        "detected_paths": sorted(
            set(detected_paths)
        ),
    }


def build_signatures(
    files: list[Path],
) -> dict[str, tuple[int, int]]:

    signatures: dict[
        str,
        tuple[int, int],
    ] = {}

    for path in files:

        signatures[
            str(path)
        ] = file_signature(path)

    return signatures


def print_header() -> None:

    print("=" * 100)
    print(
        "ARUNDA TRADER — REAL ELIGIBLE SIGNAL "
        "WATCHER HEALTH v0.2"
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
        "JSON WRITE   : NONE"
    )

    print(
        "ARTIFACT CREATION : NONE"
    )

    print(
        f"POLL SECONDS : {POLL_SECONDS}"
    )

    print("=" * 100)


def main() -> int:

    print_header()

    if not PROJECT_ROOT.exists():

        print(
            "ERROR: PROJECT ROOT NOT FOUND"
        )

        return 1

    print("=" * 100)
    print("HEALTH WATCH")
    print("=" * 100)

    previous_signatures: dict[
        str,
        tuple[int, int],
    ] = {}

    scan_number = 0

    try:

        while True:

            scan_number += 1

            files = discover_json_files()

            current_signatures = build_signatures(
                files
            )

            changed_paths = []

            all_paths = set(
                previous_signatures
            ) | set(
                current_signatures
            )

            for path_string in sorted(
                all_paths
            ):

                previous = previous_signatures.get(
                    path_string
                )

                current = current_signatures.get(
                    path_string
                )

                if previous != current:

                    changed_paths.append(
                        path_string
                    )

            newest_path, newest_mtime = newest_artifact(
                files
            )

            scan_result = scan_files(
                files
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
                "ARTIFACT CHANGES : "
                f"{len(changed_paths)}"
            )

            if changed_paths:

                print(
                    "CHANGED ARTIFACTS:"
                )

                for path_string in changed_paths:

                    print(
                        f"  {path_string}"
                    )

            if newest_path is None:

                print(
                    "NEWEST ARTIFACT : NONE"
                )

            else:

                newest_time = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(
                        newest_mtime
                    ),
                )

                print(
                    "NEWEST ARTIFACT : "
                    f"{newest_path}"
                )

                print(
                    "NEWEST ARTIFACT TIME : "
                    f"{newest_time}"
                )

            print(
                "SIGNAL OBJECTS SCANNED : "
                f"{scan_result['signal_objects']}"
            )

            print(
                "PARSE FAILURES : "
                f"{scan_result['parse_failures']}"
            )

            print(
                "ELIGIBLE DETECTIONS : "
                f"{scan_result['eligible_detections']}"
            )

            if scan_result[
                "eligible_detections"
            ] > 0:

                print("=" * 100)
                print(
                    "REAL ELIGIBLE SIGNAL DETECTED"
                )
                print("=" * 100)

                for path_string in scan_result[
                    "detected_paths"
                ]:

                    print(
                        "ARTIFACT : "
                        f"{path_string}"
                    )

                print("=" * 100)
                print(
                    "WATCHER STATUS : "
                    "REAL_ELIGIBLE_SIGNAL_FOUND"
                )
                print("=" * 100)

                print(
                    "The watcher stops here."
                )

                print(
                    "No production pipeline was executed."
                )

                print(
                    "No database was accessed."
                )

                print(
                    "No artifact was written."
                )

                return 0

            else:

                print(
                    "WATCHER STATUS : "
                    "WAIT_FOR_ELIGIBLE_SIGNAL"
                )

            previous_signatures = current_signatures

            time.sleep(
                POLL_SECONDS
            )

    except KeyboardInterrupt:

        print()
        print("=" * 100)
        print(
            "WATCHER STOPPED BY USER"
        )
        print("=" * 100)

        print(
            "SAFETY ASSERTION"
        )

        print(
            "DATABASE READ      : False"
        )

        print(
            "DATABASE WRITE     : False"
        )

        print(
            "JSON WRITE         : False"
        )

        print(
            "ARTIFACT CREATION  : False"
        )

        print(
            "ORDER CREATION     : False"
        )

        print(
            "ORDER SUBMISSION   : False"
        )

        print(
            "NETWORK ACCESS     : False"
        )

        print(
            "ARTIFACT MUTATION  : False"
        )

        print("=" * 100)

        return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )