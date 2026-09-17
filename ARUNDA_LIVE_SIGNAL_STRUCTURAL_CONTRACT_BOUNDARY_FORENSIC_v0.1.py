from __future__ import annotations

import ast
import inspect
import sys
import time
import traceback
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

TARGET_MODULE = "signal_engine"
TARGET_FUNCTION = "main"

EXPECTED_FIELDS = {
    "trend",
    "volatility",
    "momentum",
    "position",
    "acceleration",
}

TARGET_ERROR = "Invalid structural fields"

FORENSIC_NAME = (
    "ARUNDA TRADER — LIVE SIGNAL STRUCTURAL CONTRACT "
    "BOUNDARY FORENSIC v0.1"
)

MAX_RUNTIME_EVENTS = 2_000_000


# =============================================================================
# READ-ONLY RUNTIME OBSERVATION STATE
# =============================================================================

class ObservationState:
    def __init__(self) -> None:
        self.start = time.time()

        self.trace_events = 0

        self.build_structure_calls = 0
        self.load_structural_state_calls = 0
        self.build_signal_calls = 0
        self.validate_structure_calls = 0
        self.build_direction_calls = 0

        self.first_asset: str | None = None

        self.producer_objects: list[dict[str, Any]] = []
        self.boundary_objects: list[dict[str, Any]] = []
        self.consumer_objects: list[dict[str, Any]] = []

        self.error_observed = False
        self.error_asset: str | None = None

        self.stopped = False

        self.object_ids: dict[int, dict[str, Any]] = {}

        self.function_stack: list[str] = []

        self.last_exception: BaseException | None = None


STATE = ObservationState()


# =============================================================================
# SAFE VALUE SERIALIZATION
# =============================================================================

def safe_repr(value: Any, limit: int = 4000) -> str:
    try:
        text = repr(value)
    except Exception as exc:
        text = f"<repr failed: {type(exc).__name__}: {exc}>"

    if len(text) > limit:
        return text[:limit] + "...<TRUNCATED>"

    return text


def safe_dict(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    try:
        return dict(value)
    except Exception:
        return None


def field_delta(obj: Any) -> tuple[list[str], list[str], list[str]]:
    if not isinstance(obj, dict):
        return [], sorted(EXPECTED_FIELDS), []

    actual = set(obj.keys())

    missing = sorted(EXPECTED_FIELDS - actual)
    extra = sorted(actual - EXPECTED_FIELDS)

    return sorted(actual), missing, extra


# =============================================================================
# STATIC SOURCE MAP
# =============================================================================

def source_map() -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}

    files = [
        PROJECT_ROOT / "market_regime.py",
        PROJECT_ROOT / "signal_engine.py",
        PROJECT_ROOT / "signal_logic.py",
        PROJECT_ROOT / "market_regime_contract.py",
        PROJECT_ROOT / "signal_contract.py",
    ]

    for path in files:
        if not path.exists():
            continue

        try:
            tree = ast.parse(
                path.read_text(
                    encoding="utf-8",
                    errors="replace",
                ),
                filename=str(path),
            )
        except Exception:
            continue

        hits: list[dict[str, Any]] = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            if node.name not in {
                "build_structure",
                "load_structural_state",
                "build_signal",
                "validate_structure",
                "build_direction",
                "load_signals",
            }:
                continue

            for child in ast.walk(node):
                if isinstance(child, ast.Dict):
                    keys = []

                    for key in child.keys:
                        if isinstance(key, ast.Constant):
                            keys.append(str(key.value))

                    if "structure" in keys or (
                        EXPECTED_FIELDS.issubset(set(keys))
                    ):
                        hits.append(
                            {
                                "function": node.name,
                                "line": child.lineno,
                                "keys": sorted(keys),
                            }
                        )

                if isinstance(child, ast.Call):
                    fn_name = None

                    if isinstance(child.func, ast.Name):
                        fn_name = child.func.id

                    elif isinstance(child.func, ast.Attribute):
                        fn_name = child.func.attr

                    if fn_name in {
                        "build_structure",
                        "load_structural_state",
                        "build_signal",
                        "validate_structure",
                        "build_direction",
                    }:
                        hits.append(
                            {
                                "function": node.name,
                                "line": child.lineno,
                                "call": fn_name,
                            }
                        )

        result[str(path)] = hits

    return result


# =============================================================================
# OBJECT SNAPSHOT
# =============================================================================

def record_object(
    stage: str,
    function: str,
    obj: Any,
    asset: str | None,
) -> None:

    if not isinstance(obj, dict):
        return

    actual, missing, extra = field_delta(obj)

    snapshot = {
        "stage": stage,
        "function": function,
        "asset": asset,
        "object_id": id(obj),
        "actual_fields": actual,
        "missing_fields": missing,
        "extra_fields": extra,
        "object": dict(obj),
    }

    STATE.object_ids[id(obj)] = {
        "stage": stage,
        "function": function,
        "asset": asset,
        "snapshot": dict(obj),
    }

    if stage == "PRODUCER":
        STATE.producer_objects.append(snapshot)

    elif stage == "BOUNDARY":
        STATE.boundary_objects.append(snapshot)

    elif stage == "CONSUMER":
        STATE.consumer_objects.append(snapshot)


# =============================================================================
# RUNTIME TRACE
# =============================================================================

def runtime_trace(
    frame,
    event,
    arg,
):
    if STATE.stopped:
        return None

    STATE.trace_events += 1

    if STATE.trace_events > MAX_RUNTIME_EVENTS:
        STATE.stopped = True
        return None

    module = frame.f_globals.get("__name__", "")
    function = frame.f_code.co_name

    if module not in {
        "market_regime",
        "signal_engine",
        "signal_logic",
        "market_regime_contract",
        "signal_contract",
    }:
        return runtime_trace

    # -------------------------------------------------------------------------
    # FUNCTION ENTRY
    # -------------------------------------------------------------------------

    if event == "call":

        if function == "build_structure":
            STATE.build_structure_calls += 1

        elif function == "load_structural_state":
            STATE.load_structural_state_calls += 1

        elif function == "build_signal":
            STATE.build_signal_calls += 1

        elif function == "validate_structure":
            STATE.validate_structure_calls += 1

        elif function == "build_direction":
            STATE.build_direction_calls += 1

        STATE.function_stack.append(function)

        return runtime_trace

    # -------------------------------------------------------------------------
    # RETURN OBSERVATION
    # -------------------------------------------------------------------------

    if event == "return":

        if isinstance(arg, dict):

            asset = None

            for key in (
                "asset",
                "symbol",
                "market",
                "ticker",
            ):
                if key in arg and isinstance(arg[key], str):
                    asset = arg[key]
                    break

            if asset is None:
                # Try to infer from local frame.
                for key in (
                    "asset",
                    "symbol",
                    "ticker",
                ):
                    value = frame.f_locals.get(key)
                    if isinstance(value, str):
                        asset = value
                        break

            if asset is not None and STATE.first_asset is None:
                STATE.first_asset = asset

            if function == "build_structure":
                record_object(
                    "PRODUCER",
                    function,
                    arg,
                    asset,
                )

            elif function == "load_structural_state":
                record_object(
                    "BOUNDARY",
                    function,
                    arg,
                    asset,
                )

            elif function == "build_signal":
                record_object(
                    "BOUNDARY",
                    function,
                    arg,
                    asset,
                )

            elif function in {
                "validate_structure",
                "build_direction",
            }:
                record_object(
                    "CONSUMER",
                    function,
                    arg,
                    asset,
                )

        if STATE.function_stack:
            STATE.function_stack.pop()

        return runtime_trace

    # -------------------------------------------------------------------------
    # EXCEPTION OBSERVATION
    # -------------------------------------------------------------------------

    if event == "exception":

        exc_type, exc_value, _ = arg

        if (
            isinstance(exc_value, RuntimeError)
            and TARGET_ERROR in str(exc_value)
        ):
            STATE.error_observed = True
            STATE.last_exception = exc_value

            asset = (
                frame.f_locals.get("asset")
                or frame.f_locals.get("symbol")
                or frame.f_locals.get("ticker")
            )

            if isinstance(asset, str):
                STATE.error_asset = asset

        return runtime_trace

    return runtime_trace


# =============================================================================
# EXTRACT THE STRUCTURAL OBJECT CURRENTLY PASSED TO VALIDATE_STRUCTURE
# =============================================================================

def install_argument_probe() -> None:
    """
    Runtime-only tracing helper.

    No production function is replaced.
    No wrapper is injected.
    sys.settrace observes Python execution events only.
    """

    return None


# =============================================================================
# STATIC DISPLAY
# =============================================================================

def print_static_map(mapping: dict[str, list[dict[str, Any]]]) -> None:

    print()
    print("=" * 100)
    print("A) STATIC CONTRACT / BOUNDARY MAP")
    print("=" * 100)

    for file_name, hits in mapping.items():

        print()
        print(f"FILE : {file_name}")

        if not hits:
            print("  NO RELEVANT STATIC HITS")
            continue

        seen = set()

        for hit in hits:

            signature = repr(hit)

            if signature in seen:
                continue

            seen.add(signature)

            print(
                f"  LINE={hit.get('line')} "
                f"FUNCTION={hit.get('function')} "
                f"CALL={hit.get('call')} "
                f"KEYS={hit.get('keys')}"
            )


# =============================================================================
# REPORT
# =============================================================================

def print_runtime_report() -> None:

    elapsed = time.time() - STATE.start

    print()
    print("=" * 100)
    print("B) REAL RUNTIME STRUCTURAL CONTRACT OBSERVATION")
    print("=" * 100)

    print(
        f"TRACE EVENTS              : {STATE.trace_events}"
    )

    print(
        f"BUILD_STRUCTURE CALLS     : "
        f"{STATE.build_structure_calls}"
    )

    print(
        f"LOAD_STRUCTURAL_STATE     : "
        f"{STATE.load_structural_state_calls}"
    )

    print(
        f"BUILD_SIGNAL CALLS        : "
        f"{STATE.build_signal_calls}"
    )

    print(
        f"VALIDATE_STRUCTURE CALLS  : "
        f"{STATE.validate_structure_calls}"
    )

    print(
        f"BUILD_DIRECTION CALLS     : "
        f"{STATE.build_direction_calls}"
    )

    print(
        f"FIRST OBSERVED ASSET      : "
        f"{STATE.first_asset}"
    )

    print(
        f"TARGET ERROR OBSERVED     : "
        f"{STATE.error_observed}"
    )

    if STATE.error_asset:
        print(
            f"ERROR ASSET               : "
            f"{STATE.error_asset}"
        )

    print(
        f"ELAPSED SECONDS           : "
        f"{elapsed:.2f}"
    )

    # -------------------------------------------------------------------------
    # PRODUCER OBJECTS
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("C) PRODUCER OBJECTS — build_structure()")
    print("=" * 100)

    if not STATE.producer_objects:
        print("NO RUNTIME PRODUCER OBJECT CAPTURED")

    else:

        for index, item in enumerate(
            STATE.producer_objects[:20],
            start=1,
        ):
            print()
            print(f"PRODUCER OBJECT #{index}")
            print(
                f"ASSET        : {item['asset']}"
            )
            print(
                f"OBJECT ID    : {item['object_id']}"
            )
            print(
                f"ACTUAL FIELDS: {item['actual_fields']}"
            )
            print(
                f"MISSING      : {item['missing_fields']}"
            )
            print(
                f"EXTRA        : {item['extra_fields']}"
            )
            print(
                f"OBJECT       : "
                f"{safe_repr(item['object'])}"
            )

    # -------------------------------------------------------------------------
    # BOUNDARY OBJECTS
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("D) BOUNDARY OBJECTS")
    print("=" * 100)

    if not STATE.boundary_objects:
        print("NO RUNTIME BOUNDARY OBJECT CAPTURED")

    else:

        for index, item in enumerate(
            STATE.boundary_objects[:20],
            start=1,
        ):
            print()
            print(f"BOUNDARY OBJECT #{index}")
            print(
                f"STAGE        : {item['stage']}"
            )
            print(
                f"FUNCTION     : {item['function']}"
            )
            print(
                f"ASSET        : {item['asset']}"
            )
            print(
                f"OBJECT ID    : {item['object_id']}"
            )
            print(
                f"ACTUAL FIELDS: {item['actual_fields']}"
            )
            print(
                f"MISSING      : {item['missing_fields']}"
            )
            print(
                f"EXTRA        : {item['extra_fields']}"
            )
            print(
                f"OBJECT       : "
                f"{safe_repr(item['object'])}"
            )

    # -------------------------------------------------------------------------
    # CONSUMER OBJECTS
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("E) CONSUMER OBJECTS — signal_logic")
    print("=" * 100)

    if not STATE.consumer_objects:
        print("NO RUNTIME CONSUMER OBJECT CAPTURED")

    else:

        for index, item in enumerate(
            STATE.consumer_objects[:20],
            start=1,
        ):
            print()
            print(f"CONSUMER OBJECT #{index}")
            print(
                f"FUNCTION     : {item['function']}"
            )
            print(
                f"ASSET        : {item['asset']}"
            )
            print(
                f"OBJECT ID    : {item['object_id']}"
            )
            print(
                f"ACTUAL FIELDS: {item['actual_fields']}"
            )
            print(
                f"MISSING      : {item['missing_fields']}"
            )
            print(
                f"EXTRA        : {item['extra_fields']}"
            )
            print(
                f"OBJECT       : "
                f"{safe_repr(item['object'])}"
            )

    # -------------------------------------------------------------------------
    # OBJECT IDENTITY
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("F) OBJECT IDENTITY / TRANSFORMATION BOUNDARY")
    print("=" * 100)

    producer_ids = {
        item["object_id"]
        for item in STATE.producer_objects
    }

    boundary_ids = {
        item["object_id"]
        for item in STATE.boundary_objects
    }

    consumer_ids = {
        item["object_id"]
        for item in STATE.consumer_objects
    }

    print(
        f"PRODUCER OBJECT IDS : "
        f"{sorted(producer_ids)}"
    )

    print(
        f"BOUNDARY OBJECT IDS : "
        f"{sorted(boundary_ids)}"
    )

    print(
        f"CONSUMER OBJECT IDS : "
        f"{sorted(consumer_ids)}"
    )

    shared_pb = producer_ids & boundary_ids
    shared_bc = boundary_ids & consumer_ids
    shared_pc = producer_ids & consumer_ids

    print(
        f"PRODUCER == BOUNDARY OBJECT : "
        f"{sorted(shared_pb)}"
    )

    print(
        f"BOUNDARY == CONSUMER OBJECT : "
        f"{sorted(shared_bc)}"
    )

    print(
        f"PRODUCER == CONSUMER OBJECT : "
        f"{sorted(shared_pc)}"
    )

    # -------------------------------------------------------------------------
    # FINAL DECISION
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("G) CONTRACT BOUNDARY DECISION")
    print("=" * 100)

    producer_with_extra = [
        x
        for x in STATE.producer_objects
        if "structure" in x["extra_fields"]
    ]

    consumer_with_extra = [
        x
        for x in STATE.consumer_objects
        if "structure" in x["extra_fields"]
    ]

    if STATE.error_observed and producer_with_extra:

        print(
            "VERDICT : "
            "REAL_RUNTIME_PRODUCER_TO_CONSUMER_CONTRACT_VIOLATION"
        )

        print()
        print(
            "REASON  : "
            "A real runtime structural object produced by "
            "build_structure() reached the signal path with "
            "the extra field 'structure' and the target "
            "RuntimeError was observed."
        )

    elif STATE.error_observed:

        print(
            "VERDICT : "
            "REAL_RUNTIME_CONTRACT_ERROR_OBSERVED_BUT_PRODUCER_BOUNDARY_INCOMPLETE"
        )

        print()
        print(
            "REASON  : "
            "The target runtime error was observed, but the "
            "producer object could not yet be correlated "
            "completely with the consumer boundary."
        )

    else:

        print(
            "VERDICT : "
            "NO_TARGET_RUNTIME_CONTRACT_FAILURE_OBSERVED"
        )

        print()
        print(
            "REASON  : "
            "The production runtime returned without observing "
            "the target RuntimeError during this observation."
        )

    # -------------------------------------------------------------------------
    # REPAIR OWNER
    # -------------------------------------------------------------------------

    print()
    print("=" * 100)
    print("H) REPAIR OWNER — OBSERVATIONAL ONLY")
    print("=" * 100)

    if producer_with_extra:

        print(
            "PRODUCER STATUS : "
            "STRUCTURAL OBJECT CONTAINS EXTRA FIELD 'structure'"
        )

    if consumer_with_extra:

        print(
            "CONSUMER STATUS : "
            "CONSUMER ALSO OBSERVED EXTRA FIELD 'structure'"
        )

    print()
    print(
        "REPAIR ACTION : NOT PERFORMED"
    )

    print(
        "PRODUCTION SOURCE MUTATION : NONE"
    )

    print()
    print("=" * 100)
    print("I) SAFETY ASSERTION")
    print("=" * 100)

    print("PRODUCTION SOURCE MUTATION : False")
    print("DATABASE READ              : False")
    print("DATABASE WRITE             : False")
    print("JSON WRITE                 : False")
    print("ARTIFACT CREATION          : False")
    print("SIGNAL INJECTION           : False")
    print("SIGNAL MUTATION            : False")
    print("SYNTHETIC SIGNAL           : False")
    print("ORDER CREATION             : False")
    print("ORDER SUBMISSION           : False")
    print("NETWORK ACCESS BY FORENSIC : False")

    print()
    print("=" * 100)
    print(
        "END — LIVE SIGNAL STRUCTURAL CONTRACT "
        "BOUNDARY FORENSIC v0.1"
    )
    print("=" * 100)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print("=" * 100)
    print(FORENSIC_NAME)
    print("=" * 100)

    print(
        f"PROJECT ROOT          : {PROJECT_ROOT}"
    )

    print(
        f"TARGET                : "
        f"{TARGET_MODULE}:{TARGET_FUNCTION}"
    )

    print(
        "MODE                  : "
        "READ-ONLY RUNTIME OBSERVATION"
    )

    print(
        "PRODUCTION EXECUTION  : "
        "REAL RUNTIME ONLY"
    )

    print(
        "DATABASE ACCESS       : NONE"
    )

    print(
        "DATABASE WRITE        : NONE"
    )

    print(
        "JSON WRITE            : NONE"
    )

    print(
        "SOURCE MUTATION       : NONE"
    )

    print(
        "SYNTHETIC SIGNAL      : FORBIDDEN"
    )

    print()
    print("=" * 100)
    print("OBSERVATION CONTRACT")
    print("=" * 100)

    print(
        "Observe the real production signal engine only."
    )

    print(
        "Do not inject a signal."
    )

    print(
        "Do not modify structural objects."
    )

    print(
        "Do not patch production functions."
    )

    print(
        "Do not access the database."
    )

    print(
        "Do not write artifacts."
    )

    print(
        f"TARGET ERROR : {TARGET_ERROR}"
    )

    mapping = source_map()

    print_static_map(mapping)

    print()
    print("=" * 100)
    print("J) REAL PRODUCTION RUNTIME START")
    print("=" * 100)

    print(
        f"TARGET : {TARGET_MODULE}.main"
    )

    print(
        "STATUS : OBSERVING_REAL_PRODUCTION_RUNTIME"
    )

    print(
        "No production function is patched."
    )

    print(
        "No signal is injected."
    )

    print(
        "No structural object is modified."
    )

    print(
        "Press Ctrl+C to stop."
    )

    old_trace = sys.gettrace()

    try:

        sys.settrace(runtime_trace)

        module = __import__(TARGET_MODULE)

        target = getattr(module, TARGET_FUNCTION)

        try:
            target()

        except KeyboardInterrupt:

            print()
            print(
                "RUNTIME OBSERVATION INTERRUPTED BY USER"
            )

        except Exception as exc:

            STATE.last_exception = exc

            print()
            print("=" * 100)
            print("RUNTIME EXCEPTION REACHED OBSERVER")
            print("=" * 100)

            print(
                f"TYPE   : {type(exc).__name__}"
            )

            print(
                f"ERROR  : {exc}"
            )

            if (
                isinstance(exc, RuntimeError)
                and TARGET_ERROR in str(exc)
            ):
                STATE.error_observed = True

            print()
            print(
                "Production runtime was not modified."
            )

    finally:

        sys.settrace(old_trace)

    print_runtime_report()


if __name__ == "__main__":
    main()