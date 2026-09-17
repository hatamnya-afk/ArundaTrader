from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

POLL_SECONDS = 2.0

EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "_QUARANTINE_NONPRODUCTION_SYNTAX_FAILURES",
}

IDENTITY_KEYS = (
    "signal_id",
    "id",
    "row_id",
)

MAX_DEPTH = 100


def print_section(title: str) -> None:
    print("=" * 100)
    print(title)
    print("=" * 100)


def is_excluded(path: Path) -> bool:
    try:
        relative = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return True

    return any(
        part in EXCLUDED_DIRS
        for part in relative.parts
    )


def discover_json_files() -> list[Path]:
    files: list[Path] = []

    try:
        iterator = PROJECT_ROOT.rglob("*.json")
    except Exception:
        return files

    for path in iterator:
        if is_excluded(path):
            continue

        try:
            if path.is_file():
                files.append(path)
        except OSError:
            continue

    return sorted(files)


def load_json(
    path: Path,
) -> tuple[Any | None, str | None]:

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
        ) as f:
            return json.load(f), None

    except Exception as exc:
        return None, str(exc)


def walk_json(
    obj: Any,
    path: str = "$",
    depth: int = 0,
):
    if depth > MAX_DEPTH:
        return

    if isinstance(obj, dict):

        yield path, obj

        for key, value in obj.items():

            child_path = (
                f"{path}.{key}"
            )

            yield from walk_json(
                value,
                child_path,
                depth + 1,
            )

    elif isinstance(obj, list):

        for index, item in enumerate(obj):

            child_path = (
                f"{path}[{index}]"
            )

            yield from walk_json(
                item,
                child_path,
                depth + 1,
            )


def resolve_identity(
    obj: dict[str, Any],
) -> tuple[str | None, Any]:

    for key in IDENTITY_KEYS:

        if key not in obj:
            continue

        value = obj.get(key)

        if value is None:
            continue

        if isinstance(
            value,
            (str, int),
        ):
            if str(value).strip():
                return key, value

    return None, None


def is_real_eligible_signal(
    obj: dict[str, Any],
) -> bool:

    if obj.get("eligible") is not True:
        return False

    identity_key, identity_value = (
        resolve_identity(obj)
    )

    if identity_key is None:
        return False

    if identity_value is None:
        return False

    return True


def signal_summary(
    obj: dict[str, Any],
) -> dict[str, Any]:

    summary: dict[str, Any] = {}

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
            summary[key] = obj[key]

    return summary


def fingerprint_signal(
    artifact: str,
    json_path: str,
    obj: dict[str, Any],
) -> tuple[Any, ...]:

    identity_key, identity_value = (
        resolve_identity(obj)
    )

    return (
        artifact,
        json_path,
        identity_key,
        str(identity_value),
        obj.get("timestamp"),
        obj.get("asset"),
        obj.get("symbol"),
        obj.get("direction"),
    )


def scan_once(
    known_fingerprints: set[tuple[Any, ...]],
) -> tuple[
    dict[str, Any] | None,
    int,
    int,
]:

    files = discover_json_files()

    parse_failures = 0
    scanned_objects = 0

    for path in files:

        data, error = load_json(path)

        if error is not None:

            parse_failures += 1

            continue

        if data is None:
            continue

        for json_path, obj in walk_json(data):

            if not isinstance(obj, dict):
                continue

            scanned_objects += 1

            if not is_real_eligible_signal(obj):
                continue

            fingerprint = fingerprint_signal(
                str(path),
                json_path,
                obj,
            )

            if fingerprint in known_fingerprints:
                continue

            known_fingerprints.add(
                fingerprint
            )

            return (
                {
                    "artifact": str(path),
                    "json_path": json_path,
                    "identity_key": (
                        resolve_identity(obj)[0]
                    ),
                    "identity_value": (
                        resolve_identity(obj)[1]
                    ),
                    "signal": signal_summary(obj),
                    "raw_object": obj,
                },
                scanned_objects,
                parse_failures,
            )

    return (
        None,
        scanned_objects,
        parse_failures,
    )


def main() -> int:

    print("=" * 100)
    print(
        "ARUNDA TRADER — REAL ELIGIBLE SIGNAL "
        "WATCHER v0.1"
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

    if not PROJECT_ROOT.exists():

        print(
            "ERROR: PROJECT ROOT NOT FOUND"
        )

        return 1

    print_section(
        "WATCH TARGET"
    )

    print(
        "The watcher scans existing and newly "
        "appearing JSON artifacts."
    )

    print(
        "It stops only when a REAL eligible signal "
        "with a resolvable identity is found."
    )

    print(
        "No synthetic signal will be created."
    )

    print(
        "No production Python pipeline will be executed."
    )

    print(
        "No database will be accessed."
    )

    print_section(
        "INITIAL SCAN"
    )

    known_fingerprints: set[
        tuple[Any, ...]
    ] = set()

    initial_files = discover_json_files()

    print(
        f"JSON ARTIFACTS CURRENTLY DISCOVERED : "
        f"{len(initial_files)}"
    )

    signal, scanned, parse_failures = scan_once(
        known_fingerprints
    )

    print(
        f"SIGNAL OBJECTS SCANNED : "
        f"{scanned}"
    )

    print(
        f"JSON PARSE FAILURES     : "
        f"{parse_failures}"
    )

    if signal is not None:

        print_section(
            "REAL ELIGIBLE SIGNAL FOUND"
        )

        print(
            "REAL ELIGIBLE SIGNAL : True"
        )

        print(
            f"ARTIFACT : "
            f"{signal['artifact']}"
        )

        print(
            f"JSON PATH : "
            f"{signal['json_path']}"
        )

        print(
            f"IDENTITY KEY : "
            f"{signal['identity_key']}"
        )

        print(
            f"IDENTITY VALUE : "
            f"{signal['identity_value']}"
        )

        print(
            "SIGNAL SUMMARY:"
        )

        for key, value in signal[
            "signal"
        ].items():

            print(
                f"  {key} : {value}"
            )

        print_section(
            "FIRST REAL ELIGIBLE SIGNAL TARGET"
        )

        print(
            f"TARGET ARTIFACT : "
            f"{signal['artifact']}"
        )

        print(
            f"TARGET JSON PATH : "
            f"{signal['json_path']}"
        )

        print(
            f"TARGET ID : "
            f"{signal['identity_value']}"
        )

        print_section(
            "FORENSIC HANDOFF"
        )

        print(
            "NEXT TARGET:"
        )

        print(
            "REAL_ELIGIBLE_SIGNAL"
        )

        print(
            "→ ORDER-INTENT GENERATOR"
        )

        print(
            "→ ORDER-INTENT VALIDATION"
        )

        print(
            "→ EXECUTION GATE"
        )

        print(
            "→ DOWNSTREAM RELEASE"
        )

        print_section(
            "SAFETY ASSERTION"
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
            "END — REAL ELIGIBLE SIGNAL CAPTURED"
        )
        print("=" * 100)

        return 0

    print_section(
        "WATCHING"
    )

    print(
        "STATUS : WAIT_FOR_ELIGIBLE_SIGNAL"
    )

    print(
        "The watcher is now waiting for a real "
        "eligible signal to appear in project JSON artifacts."
    )

    print(
        "Press Ctrl+C to stop."
    )

    try:

        while True:

            time.sleep(
                POLL_SECONDS
            )

            signal, scanned, parse_failures = (
                scan_once(
                    known_fingerprints
                )
            )

            if signal is None:
                continue

            print()

            print_section(
                "REAL ELIGIBLE SIGNAL FOUND"
            )

            print(
                "REAL ELIGIBLE SIGNAL : True"
            )

            print(
                f"ARTIFACT : "
                f"{signal['artifact']}"
            )

            print(
                f"JSON PATH : "
                f"{signal['json_path']}"
            )

            print(
                f"IDENTITY KEY : "
                f"{signal['identity_key']}"
            )

            print(
                f"IDENTITY VALUE : "
                f"{signal['identity_value']}"
            )

            print(
                "SIGNAL SUMMARY:"
            )

            for key, value in signal[
                "signal"
            ].items():

                print(
                    f"  {key} : {value}"
                )

            print_section(
                "FORENSIC HANDOFF"
            )

            print(
                "REAL_ELIGIBLE_SIGNAL"
            )

            print(
                "→ ORDER-INTENT GENERATOR"
            )

            print(
                "→ ORDER-INTENT VALIDATION"
            )

            print(
                "→ EXECUTION GATE"
            )

            print(
                "→ DOWNSTREAM RELEASE"
            )

            print_section(
                "SAFETY ASSERTION"
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
                "END — REAL ELIGIBLE SIGNAL CAPTURED"
            )
            print("=" * 100)

            return 0

    except KeyboardInterrupt:

        print()
        print_section(
            "WATCHER STOPPED"
        )

        print(
            "VERDICT : WAIT_FOR_ELIGIBLE_SIGNAL"
        )

        print(
            "REASON  : Watcher was stopped before "
            "a real eligible signal was observed."
        )

        print_section(
            "SAFETY ASSERTION"
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
            "END — READ ONLY WATCHER"
        )
        print("=" * 100)

        return 0


if __name__ == "__main__":
    raise SystemExit(main())