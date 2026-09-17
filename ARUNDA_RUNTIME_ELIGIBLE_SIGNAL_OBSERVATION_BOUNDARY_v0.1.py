from __future__ import annotations

import argparse
import importlib
import inspect
import os
import runpy
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader").resolve()

STOP_AFTER_FIRST = True

IDENTITY_KEYS = (
    "signal_id",
    "id",
    "signal_identity",
    "snapshot_id",
    "row_id",
    "market_id",
    "symbol",
    "ticker",
)

SIGNAL_KEYS = (
    "signal",
    "eligible_signal",
    "eligible_signals",
    "fusion_signal",
    "signal_data",
    "artifact",
)


class RuntimeObservation:
    def __init__(self) -> None:
        self.events = 0
        self.calls = 0
        self.eligible_detections = 0
        self.first_signal: dict[str, Any] | None = None
        self.started_at = time.time()

    def emit_header(self) -> None:
        print("=" * 100)
        print("ARUNDA TRADER — RUNTIME ELIGIBLE SIGNAL OBSERVATION BOUNDARY v0.1")
        print("=" * 100)
        print(f"PROJECT ROOT          : {PROJECT_ROOT}")
        print("MODE                  : READ-ONLY RUNTIME OBSERVATION")
        print("DATABASE WRITE        : NONE")
        print("JSON WRITE            : NONE")
        print("ARTIFACT CREATION     : NONE")
        print("ORDER CREATION        : NONE")
        print("ORDER SUBMISSION      : NONE")
        print("NETWORK ACCESS        : NOT PERFORMED BY OBSERVER")
        print("SYNTHETIC SIGNAL      : FORBIDDEN")
        print("=" * 100)
        print()
        print("OBSERVATION CONTRACT")
        print("-" * 100)
        print("Observe the real production runtime only.")
        print("Do not create an eligible signal.")
        print("Do not mutate signal objects.")
        print("Do not write files.")
        print("Do not access the database from this observer.")
        print("Stop on the first runtime object satisfying:")
        print("    eligible == True")
        print("and having a resolvable signal identity.")
        print("=" * 100)

    @staticmethod
    def safe_repr(value: Any, limit: int = 500) -> str:
        try:
            text = repr(value)
        except Exception:
            return "<repr-failed>"

        if len(text) > limit:
            return text[:limit] + "...<truncated>"
        return text

    @staticmethod
    def identity_from_mapping(obj: dict[str, Any]) -> dict[str, Any]:
        identity: dict[str, Any] = {}

        for key in IDENTITY_KEYS:
            if key in obj and obj[key] is not None:
                identity[key] = obj[key]

        return identity

    def is_real_eligible_mapping(
        self,
        obj: dict[str, Any],
    ) -> bool:
        if obj.get("eligible") is not True:
            return False

        identity = self.identity_from_mapping(obj)

        if identity:
            return True

        # Some real runtime schemas may wrap the identity.
        for key in SIGNAL_KEYS:
            nested = obj.get(key)

            if isinstance(nested, dict):
                nested_identity = self.identity_from_mapping(nested)

                if nested_identity:
                    return True

        return False

    def extract_identity(
        self,
        obj: dict[str, Any],
    ) -> dict[str, Any]:
        identity = self.identity_from_mapping(obj)

        if identity:
            return identity

        for key in SIGNAL_KEYS:
            nested = obj.get(key)

            if isinstance(nested, dict):
                nested_identity = self.identity_from_mapping(nested)

                if nested_identity:
                    return nested_identity

        return {}

    def inspect_value(
        self,
        value: Any,
        location: str,
        depth: int = 0,
    ) -> bool:
        if depth > 5:
            return False

        if isinstance(value, dict):
            if self.is_real_eligible_mapping(value):
                identity = self.extract_identity(value)

                self.eligible_detections += 1

                self.first_signal = {
                    "identity": identity,
                    "object": value,
                    "location": location,
                }

                return True

            for key, child in list(value.items()):
                child_location = f"{location}[{key!r}]"

                if self.inspect_value(
                    child,
                    child_location,
                    depth + 1,
                ):
                    return True

            return False

        if isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                child_location = f"{location}[{index}]"

                if self.inspect_value(
                    child,
                    child_location,
                    depth + 1,
                ):
                    return True

            return False

        return False

    def inspect_frame(self, frame) -> bool:
        try:
            locals_snapshot = dict(frame.f_locals)
        except Exception:
            return False

        for name, value in locals_snapshot.items():
            if name.startswith("__"):
                continue

            if self.inspect_value(
                value,
                f"{frame.f_code.co_name}.local[{name!r}]",
            ):
                return True

        return False

    def trace(self, frame, event, arg):
        self.events += 1

        filename = Path(frame.f_code.co_filename).resolve()

        try:
            inside_project = (
                filename == PROJECT_ROOT
                or PROJECT_ROOT in filename.parents
            )
        except Exception:
            inside_project = False

        if not inside_project:
            return self.trace

        if event == "call":
            self.calls += 1

            if self.calls % 1000 == 0:
                elapsed = time.time() - self.started_at

                print(
                    f"[RUNTIME] calls={self.calls} "
                    f"events={self.events} "
                    f"elapsed={elapsed:.1f}s"
                )

        elif event in ("line", "return"):
            if self.inspect_frame(frame):
                self.report_and_stop()

        return self.trace

    def report_and_stop(self) -> None:
        if self.first_signal is None:
            return

        signal = self.first_signal

        print()
        print("=" * 100)
        print("REAL RUNTIME ELIGIBLE SIGNAL DETECTED")
        print("=" * 100)

        print(f"DETECTION NUMBER : {self.eligible_detections}")
        print(f"LOCATION         : {signal['location']}")
        print()

        print("RESOLVED IDENTITY")
        print("-" * 100)

        for key, value in signal["identity"].items():
            print(f"{key:20} : {self.safe_repr(value)}")

        print()
        print("RUNTIME OBJECT")
        print("-" * 100)
        print(self.safe_repr(signal["object"], limit=3000))

        print()
        print("OBSERVATION DECISION")
        print("-" * 100)
        print("REAL ELIGIBLE SIGNAL : TRUE")
        print("SYNTHETIC SIGNAL     : FALSE")
        print("IDENTITY RESOLVED    : TRUE")
        print("RUNTIME OBSERVED     : TRUE")
        print()
        print(
            "VERDICT : FIRST_REAL_RUNTIME_ELIGIBLE_SIGNAL_CAPTURED"
        )

        print()
        print("NEXT TRACE TARGET")
        print("-" * 100)
        print(
            "REAL ELIGIBLE SIGNAL"
            " → ORDER-INTENT GENERATOR"
            " → VALIDATION"
            " → EXECUTION GATE"
            " → DOWNSTREAM RELEASE"
        )

        print("=" * 100)

        raise StopRuntimeObservation()


class StopRuntimeObservation(Exception):
    pass


def load_target(target: str):
    """
    Supported:

        module:function

    Example:

        signal_engine:main

    or:

        signal_engine:process_signals
    """

    if ":" not in target:
        raise ValueError(
            "Target must use module:function format."
        )

    module_name, function_name = target.split(":", 1)

    sys.path.insert(0, str(PROJECT_ROOT))

    module = importlib.import_module(module_name)

    function = getattr(module, function_name)

    if not callable(function):
        raise TypeError(
            f"Target is not callable: {target}"
        )

    return function


def run_target(args) -> int:
    observer = RuntimeObservation()

    observer.emit_header()

    print()
    print("=" * 100)
    print("RUNTIME TARGET")
    print("=" * 100)
    print(f"TARGET : {args.target}")
    print("=" * 100)
    print()
    print("STATUS : OBSERVING_REAL_PRODUCTION_RUNTIME")
    print("Press Ctrl+C to stop.")
    print()

    target = load_target(args.target)

    print(
        f"LOADED : {target.__module__}.{target.__name__}"
    )

    source_file = inspect.getsourcefile(target)

    if source_file:
        print(f"SOURCE : {Path(source_file).resolve()}")

    print()
    print("-" * 100)
    print("RUNTIME OBSERVATION START")
    print("-" * 100)

    previous_trace = sys.gettrace()

    sys.settrace(observer.trace)

    try:
        result = target()

        print()
        print("=" * 100)
        print("RUNTIME RETURNED WITHOUT ELIGIBLE SIGNAL")
        print("=" * 100)
        print(f"CALLS              : {observer.calls}")
        print(f"TRACE EVENTS       : {observer.events}")
        print(
            f"ELIGIBLE DETECTIONS: "
            f"{observer.eligible_detections}"
        )
        print("VERDICT             : NO_REAL_RUNTIME_ELIGIBLE_SIGNAL")
        print("=" * 100)

        return 0

    except StopRuntimeObservation:
        return 0

    except KeyboardInterrupt:
        print()
        print()
        print("=" * 100)
        print("RUNTIME OBSERVATION INTERRUPTED")
        print("=" * 100)
        print(f"CALLS              : {observer.calls}")
        print(f"TRACE EVENTS       : {observer.events}")
        print(
            f"ELIGIBLE DETECTIONS: "
            f"{observer.eligible_detections}"
        )
        print("=" * 100)

        return 130

    finally:
        sys.settrace(previous_trace)


def run_script(args) -> int:
    observer = RuntimeObservation()

    observer.emit_header()

    script = Path(args.script).resolve()

    if not script.exists():
        raise FileNotFoundError(script)

    print()
    print("=" * 100)
    print("RUNTIME SCRIPT TARGET")
    print("=" * 100)
    print(f"SCRIPT : {script}")
    print("=" * 100)
    print()
    print("STATUS : OBSERVING_REAL_PRODUCTION_RUNTIME")
    print()

    previous_trace = sys.gettrace()

    sys.settrace(observer.trace)

    try:
        runpy.run_path(
            str(script),
            run_name="__main__",
        )

        print()
        print("=" * 100)
        print("RUNTIME RETURNED WITHOUT ELIGIBLE SIGNAL")
        print("=" * 100)
        print(f"CALLS              : {observer.calls}")
        print(f"TRACE EVENTS       : {observer.events}")
        print(
            f"ELIGIBLE DETECTIONS: "
            f"{observer.eligible_detections}"
        )
        print("VERDICT             : NO_REAL_RUNTIME_ELIGIBLE_SIGNAL")
        print("=" * 100)

        return 0

    except StopRuntimeObservation:
        return 0

    except KeyboardInterrupt:
        print()
        print("=" * 100)
        print("RUNTIME OBSERVATION INTERRUPTED")
        print("=" * 100)
        return 130

    finally:
        sys.settrace(previous_trace)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "READ-ONLY runtime observation boundary for "
            "the first real eligible signal."
        )
    )

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "--target",
        help="Production target in module:function format.",
    )

    group.add_argument(
        "--script",
        help="Production Python entrypoint script.",
    )

    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)

    if args.target:
        return run_target(args)

    return run_script(args)


if __name__ == "__main__":
    raise SystemExit(main())