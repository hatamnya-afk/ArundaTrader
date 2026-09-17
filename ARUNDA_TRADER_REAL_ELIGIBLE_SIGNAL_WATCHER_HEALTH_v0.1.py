from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

POLL_SECONDS = 5.0

ELIGIBLE_KEYS = {
    "eligible",
    "is_eligible",
}

IDENTITY_KEYS = {
    "id",
    "signal_id",
    "row_id",
    "signal_identity",
}

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES",
}


def print_line() -> None:
    print("=" * 100)


def load_json(path: Path) -> Any:
    with path.open(
        "r",
        encoding="utf-8-sig",
    ) as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def is_excluded(path: Path) -> bool:
    try:
        relative = path.relative_to(
            PROJECT_ROOT
        )
    except ValueError:
        return True

    return any(
        part in EXCLUDED_DIRS
        for part in relative.parts
    )


def discover_json_files() -> list[Path]:
    files: list[Path] = []

    for path in PROJECT_ROOT.rglob("*.json"):

        if not path.is_file():
            continue

        if is_excluded(path):
            continue

        files.append(path)

    return sorted(files)


def find_eligible_objects(
    obj: Any,
    path: str = "$",
) -> list[dict[str, Any]]:

    found: list[dict[str, Any]] = []

    if isinstance(obj, dict):

        eligible_value = None
        eligible_key = None

        for key, value in obj.items():

            if key.lower() in ELIGIBLE_KEYS:
                eligible_key = key
                eligible_value = value
                break

        if eligible_value is True:

            identity = None
            identity_key = None

            for key, value in obj.items():

                if (
                    key.lower()
                    in IDENTITY_KEYS
                ):
                    if (
                        isinstance(
                            value,
                            (
                                str,
                                int,
                            ),
                        )
                    ):
                        identity = value
                        identity_key = key
                        break

            if identity is not None:

                found.append(
                    {
                        "path": path,
                        "identity": identity,
                        "identity_key": identity_key,
                        "eligible_key": eligible_key,
                        "object": obj,
                    }
                )

        for key, value in obj.items():

            child_path = (
                f"{path}.{key}"
            )

            found.extend(
                find_eligible_objects(
                    value,
                    child_path,
                )
            )

    elif isinstance(obj, list):

        for index, item in enumerate(obj):

            child_path = (
                f"{path}[{index}]"
            )

            found.extend(
                find_eligible_objects(
                    item,
                    child_path,
                )
            )

    return found


def snapshot_files(
    files: list[Path],
) -> dict[str, dict[str, Any]]:

    snapshot: dict[
        str,
        dict[str, Any],
    ] = {}

    for path in files:

        try:

            stat = path.stat()

            snapshot[str(path)] = {
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
                "sha256": sha256_file(path),
            }

        except (
            OSError,
            PermissionError,
        ):
            continue

    return snapshot


def scan_artifacts(
    files: list[Path],
) -> dict[str, Any]:

    signal_objects = 0
    eligible_objects = []

    parse_failures = []

    for path in files:

        try:
            data = load_json(path)

        except Exception as exc:

            parse_failures.append(
                {
                    "path": str(path),
                    "error": str(exc),
                }
            )

            continue

        objects = find_eligible_objects(
            data
        )

        if objects:

            for item in objects:

                item["artifact"] = str(
                    path
                )

                eligible_objects.append(
                    item
                )

        signal_objects += count_signal_like(
            data
        )

    return {
        "signal_objects": signal_objects,
        "eligible_objects": eligible_objects,
        "eligible_count": len(
            eligible_objects
        ),
        "parse_failures": parse_failures,
    }


def count_signal_like(
    obj: Any,
) -> int:

    count = 0

    if isinstance(obj, dict):

        has_signal_fields = (
            (
                "eligible" in obj
                or "is_eligible" in obj
            )
            and (
                "id" in obj
                or "signal_id" in obj
                or "row_id" in obj
            )
        )

        if has_signal_fields:
            count += 1

        for value in obj.values():

            count += count_signal_like(
                value
            )

    elif isinstance(obj, list):

        for item in obj:

            count += count_signal_like(
                item
            )

    return count


def print_initial_report(
    files: list[Path],
    scan: dict[str, Any],
) -> None:

    print_line()

    print(
        "ARUNDA TRADER — REAL ELIGIBLE SIGNAL "
        "WATCHER HEALTH v0.1"
    )

    print_line()

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
        "PYTHON PIPELINE EXECUTION : NONE"
    )

    print(
        "JSON WRITE   : NONE"
    )

    print(
        "ARTIFACT CREATION : NONE"
    )

    print_line()

    print(
        "A) INITIAL ARTIFACT STATE"
    )

    print_line()

    print(
        f"JSON ARTIFACTS : {len(files)}"
    )

    print(
        f"SIGNAL OBJECTS : "
        f"{scan['signal_objects']}"
    )

    print(
        f"ELIGIBLE OBJECTS : "
        f"{scan['eligible_count']}"
    )

    print(
        f"JSON PARSE FAILURES : "
        f"{len(scan['parse_failures'])}"
    )

    if scan["parse_failures"]:

        for item in scan[
            "parse_failures"
        ]:

            print()

            print(
                f"PARSE FAILURE : "
                f"{item['path']}"
            )

            print(
                f"ERROR : "
                f"{item['error']}"
            )

    if scan["eligible_objects"]:

        print_line()

        print(
            "REAL ELIGIBLE SIGNAL DETECTED"
        )

        print_line()

        for item in scan[
            "eligible_objects"
        ]:

            print(
                f"ARTIFACT : "
                f"{item['artifact']}"
            )

            print(
                f"JSON PATH : "
                f"{item['path']}"
            )

            print(
                f"IDENTITY KEY : "
                f"{item['identity_key']}"
            )

            print(
                f"IDENTITY : "
                f"{item['identity']}"
            )

    print_line()


def main() -> int:

    if not PROJECT_ROOT.exists():

        print(
            f"ERROR: PROJECT ROOT NOT FOUND: "
            f"{PROJECT_ROOT}"
        )

        return 1

    print_line()

    print(
        "STARTING READ-ONLY WATCHER HEALTH"
    )

    print_line()

    previous_snapshot: dict[
        str,
        dict[str, Any],
    ] = {}

    first_scan = True

    try:

        while True:

            files = discover_json_files()

            current_snapshot = snapshot_files(
                files
            )

            changed = []

            if not first_scan:

                previous_paths = set(
                    previous_snapshot
                )

                current_paths = set(
                    current_snapshot
                )

                added = (
                    current_paths
                    - previous_paths
                )

                removed = (
                    previous_paths
                    - current_paths
                )

                common = (
                    current_paths
                    & previous_paths
                )

                modified = {
                    path
                    for path in common
                    if (
                        current_snapshot[path]
                        != previous_snapshot[path]
                    )
                }

                changed = sorted(
                    set(added)
                    | set(removed)
                    | modified
                )

            scan = scan_artifacts(
                files
            )

            now = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            print_line()

            print(
                f"HEARTBEAT : {now}"
            )

            print(
                f"JSON ARTIFACTS : "
                f"{len(files)}"
            )

            print(
                f"SIGNAL OBJECTS SCANNED : "
                f"{scan['signal_objects']}"
            )

            print(
                f"JSON PARSE FAILURES : "
                f"{len(scan['parse_failures'])}"
            )

            print(
                f"ARTIFACT CHANGES SINCE "
                f"LAST HEARTBEAT : "
                f"{len(changed)}"
            )

            if changed:

                print()

                print(
                    "CHANGED ARTIFACTS:"
                )

                for path in changed:

                    print(
                        f"  {path}"
                    )

            print()

            print(
                "NEWEST ARTIFACT:"
            )

            if files:

                newest = max(
                    files,
                    key=lambda p: (
                        p.stat().st_mtime_ns
                    ),
                )

                stat = newest.stat()

                print(
                    f"  PATH : {newest}"
                )

                print(
                    f"  SIZE : {stat.st_size}"
                )

                print(
                    "  MTIME : "
                    f"{time.strftime('%Y-%m-%d %H:%M:%S', "
                    f"time.localtime(stat.st_mtime))}"
                )

            else:

                print(
                    "  NONE"
                )

            print()

            print(
                "ELIGIBLE DETECTIONS : "
                f"{scan['eligible_count']}"
            )

            if scan["eligible_objects"]:

                print_line()

                print(
                    "REAL ELIGIBLE SIGNAL FOUND"
                )

                print_line()

                for item in scan[
                    "eligible_objects"
                ]:

                    print(
                        f"ARTIFACT : "
                        f"{item['artifact']}"
                    )

                    print(
                        f"JSON PATH : "
                        f"{item['path']}"
                    )

                    print(
                        f"IDENTITY : "
                        f"{item['identity']}"
                    )

                    print(
                        f"IDENTITY KEY : "
                        f"{item['identity_key']}"
                    )

                    print(
                        f"OBJECT : "
                        f"{item['object']}"
                    )

                print_line()

                print(
                    "STATUS : REAL_ELIGIBLE_SIGNAL_FOUND"
                )

                print(
                    "ACTION : STOP WATCHING AND "
                    "TRACE THIS EXACT SIGNAL"
                )

                print_line()

                return 0

            else:

                print(
                    "STATUS : "
                    "WAIT_FOR_ELIGIBLE_SIGNAL"
                )

            previous_snapshot = (
                current_snapshot
            )

            first_scan = False

            time.sleep(
                POLL_SECONDS
            )

    except KeyboardInterrupt:

        print()

        print_line()

        print(
            "WATCHER HEALTH STOPPED "
            "BY USER"
        )

        print(
            "MODE : READ ONLY"
        )

        print_line()

        return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )