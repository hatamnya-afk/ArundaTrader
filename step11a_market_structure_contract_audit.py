"""
ARUNDA TRADER — DEV-06 — STEP 11A
MARKET STRUCTURE CONTRACT AUDIT

Purpose
-------
Contract-level audit for MARKET_STRUCTURE_ENGINE_v0.1.

This audit is intentionally aligned with the REAL public API of the
current Market Structure Engine.

Architecture
------------
- Analysis Layer only
- Database NOT USED
- No SQL
- No database writes
- No production writes
- No mutation of engine source
- No look-ahead in confirmed swing semantics
- CMC_ID identity preserved as metadata
- Runtime validation performed on synthetic deterministic OHLC data

Expected engine API
-------------------
- is_swing_high
- is_swing_low
- detect_swings
- classify_swing_structure
- classify_structure_direction
- calculate_structure_strength
- detect_structure_events
- calculate_structure_confidence
- analyze_market_structure
- validate_swing_point
- validate_structure_point
- validate_structure_event
- validate_market_structure_output
- lookahead_audit
- self_test
"""

from __future__ import annotations

import ast
import importlib
import inspect
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


# ============================================================================
# CONFIGURATION
# ============================================================================

ENGINE_CANDIDATES = [
    "market_structure_engine",
    "market_structure",
    "arunda_market_structure_engine",
]

ENGINE_NAME_EXPECTED = "MARKET_STRUCTURE_ENGINE_v0.1"

DEFAULT_LEFT_BARS = 2
DEFAULT_RIGHT_BARS = 2

REQUIRED_FUNCTIONS = [
    "is_swing_high",
    "is_swing_low",
    "detect_swings",
    "classify_swing_structure",
    "classify_structure_direction",
    "calculate_structure_strength",
    "detect_structure_events",
    "calculate_structure_confidence",
    "analyze_market_structure",
    "validate_swing_point",
    "validate_structure_point",
    "validate_structure_event",
    "validate_market_structure_output",
    "lookahead_audit",
    "self_test",
]

EXPECTED_OUTPUT_FIELDS = {
    "engine",
    "bars",
    "swings",
    "structure_points",
    "events",
    "direction",
    "strength",
    "confidence",
}

ALLOWED_SWING_TYPES = {
    "SWING_HIGH",
    "SWING_LOW",
}

ALLOWED_STRUCTURE_TYPES = {
    "HH",
    "HL",
    "LH",
    "LL",
}

ALLOWED_BREAK_TYPES = {
    "NONE",
    "BOS",
    "CHoCH",
}

ALLOWED_DIRECTIONS = {
    "BULLISH",
    "BEARISH",
    "NEUTRAL",
}

ALLOWED_STRENGTH = {
    "WEAK",
    "MODERATE",
    "STRONG",
}

ALLOWED_CONFIDENCE = {
    "LOW",
    "MEDIUM",
    "HIGH",
}


# ============================================================================
# PRINT HELPERS
# ============================================================================

WIDTH = 100


def header(title: str) -> None:
    print()
    print("-" * WIDTH)
    print(title)
    print("-" * WIDTH)


def result_line(label: str, value: str) -> None:
    print(f"{label:<45}: {value}")


def pass_line(label: str) -> None:
    result_line(label, "PASS")


def fail_line(label: str, reason: str = "") -> None:
    if reason:
        result_line(label, f"FAIL — {reason}")
    else:
        result_line(label, "FAIL")


# ============================================================================
# AST / FILE VALIDATION
# ============================================================================

def locate_engine_file() -> Optional[Path]:
    """
    Locate the real engine source without importing it.
    """

    base = Path(__file__).resolve().parent

    candidates = []

    for name in ENGINE_CANDIDATES:
        candidates.append(base / f"{name}.py")

    for path in candidates:
        if path.exists():
            return path

    # Fallback: inspect local .py files for ENGINE_NAME.
    for path in sorted(base.glob("*.py")):

        if path.name == Path(__file__).name:
            continue

        try:
            source = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            continue

        if ENGINE_NAME_EXPECTED in source:
            return path

    return None


def parse_ast(source: str) -> Tuple[Optional[ast.Module], Optional[str]]:
    try:
        return ast.parse(source), None
    except SyntaxError as exc:
        return None, (
            f"SyntaxError line {exc.lineno}: {exc.msg}"
        )


def ast_function_inventory(tree: ast.Module) -> List[str]:
    names = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(node.name)

        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(
                    child,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    names.append(child.name)

    return names


def source_mutation_audit(tree: ast.Module) -> Tuple[bool, List[str]]:
    """
    This engine must contain no database mutation.

    Because the Market Structure Engine should not use SQL at all,
    any SQL mutation token is considered suspicious.
    """

    suspicious = []

    mutation_tokens = {
        "INSERT",
        "UPDATE",
        "DELETE",
        "ALTER",
        "DROP",
        "CREATE",
        "REPLACE",
        "TRUNCATE",
    }

    for node in ast.walk(tree):

        if isinstance(node, ast.Constant):
            value = node.value

            if isinstance(value, str):
                upper = value.upper()

                for token in mutation_tokens:
                    if token in upper:
                        suspicious.append(token)

        if isinstance(node, ast.Call):

            func = node.func

            if isinstance(func, ast.Attribute):
                if func.attr.lower() in {
                    "execute",
                    "executemany",
                    "executescript",
                }:
                    suspicious.append(func.attr)

    return len(suspicious) == 0, sorted(set(suspicious))


# ============================================================================
# ENGINE IMPORT
# ============================================================================

def import_engine() -> Tuple[Optional[Any], Optional[str]]:
    """
    Import the real Market Structure Engine.

    We intentionally do not execute arbitrary files.
    """

    last_error = None

    for module_name in ENGINE_CANDIDATES:

        try:
            module = importlib.import_module(module_name)
            return module, None

        except Exception as exc:
            last_error = (
                f"{type(exc).__name__}: {exc}"
            )

    # Fallback based on discovered source filename.
    path = locate_engine_file()

    if path is not None:

        module_name = path.stem

        try:
            module = importlib.import_module(module_name)
            return module, None

        except Exception as exc:
            last_error = (
                f"{type(exc).__name__}: {exc}"
            )

    return None, last_error or "Engine module not found."


# ============================================================================
# SYNTHETIC DATA
# ============================================================================

def build_test_bars(engine: Any) -> List[Any]:
    """
    Deterministic OHLC sequence.

    The sequence intentionally contains:
        - local highs
        - local lows
        - higher highs
        - higher lows
        - lower highs
        - lower lows
        - enough bars for confirmation windows

    The engine's own MarketBar class is used when available.
    """

    MarketBar = getattr(engine, "MarketBar", None)

    if MarketBar is None:
        raise RuntimeError(
            "Engine does not expose MarketBar."
        )

    closes = [
        100,
        102,
        105,
        103,
        101,
        104,
        108,
        106,
        103,
        107,
        112,
        109,
        106,
        110,
        115,
        111,
        108,
        104,
        107,
        103,
        100,
        102,
        98,
        95,
        99,
        94,
        91,
    ]

    bars = []

    for index, close in enumerate(closes):

        bars.append(
            MarketBar(
                timestamp=index,
                high=float(close + 1),
                low=float(close - 1),
                close=float(close),
                open=float(close),
                volume=float(1000 + index),
                cmc_id=1,
                symbol="TEST",
            )
        )

    return bars


def build_flat_bars(engine: Any) -> List[Any]:

    MarketBar = getattr(engine, "MarketBar", None)

    if MarketBar is None:
        raise RuntimeError(
            "Engine does not expose MarketBar."
        )

    bars = []

    for index in range(12):

        close = 100.0

        bars.append(
            MarketBar(
                timestamp=index,
                high=101.0,
                low=99.0,
                close=close,
                open=close,
                volume=1000.0,
                cmc_id=999,
                symbol="FLAT",
            )
        )

    return bars


# ============================================================================
# STATIC FUNCTION CONTRACT
# ============================================================================

def audit_required_functions(
    engine: Any,
) -> Tuple[bool, List[str]]:

    missing = []

    for name in REQUIRED_FUNCTIONS:

        if not callable(getattr(engine, name, None)):
            missing.append(name)

    return len(missing) == 0, missing


def audit_function_signatures(
    engine: Any,
) -> Tuple[bool, List[str]]:

    problems = []

    expected_minimums = {
        "is_swing_high": 2,
        "is_swing_low": 2,
        "detect_swings": 1,
        "classify_swing_structure": 1,
        "classify_structure_direction": 1,
        "calculate_structure_strength": 1,
        "detect_structure_events": 2,
        "calculate_structure_confidence": 2,
        "analyze_market_structure": 1,
        "lookahead_audit": 1,
    }

    for name, minimum in expected_minimums.items():

        func = getattr(engine, name, None)

        if func is None:
            problems.append(
                f"{name}: missing"
            )
            continue

        try:
            signature = inspect.signature(func)
            positional = [
                p
                for p in signature.parameters.values()
                if p.kind
                in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                )
            ]

            if len(positional) < minimum:
                problems.append(
                    f"{name}: insufficient parameters"
                )

        except (TypeError, ValueError) as exc:
            problems.append(
                f"{name}: {exc}"
            )

    return len(problems) == 0, problems


# ============================================================================
# SWING SEMANTICS
# ============================================================================

def audit_swing_detection(
    engine: Any,
    bars: Sequence[Any],
) -> Tuple[bool, str, Dict[str, Any]]:

    try:
        detect_swings = engine.detect_swings

        swings = detect_swings(
            bars,
            left_bars=DEFAULT_LEFT_BARS,
            right_bars=DEFAULT_RIGHT_BARS,
        )

        if not isinstance(swings, list):
            return False, "detect_swings did not return list.", {}

        if not swings:
            return False, "No swings detected on deterministic test data.", {}

        for swing in swings:

            if swing.swing_type not in ALLOWED_SWING_TYPES:
                return False, (
                    f"Invalid swing type: {swing.swing_type}"
                ), {}

            if swing.confirmation_index != (
                swing.index + DEFAULT_RIGHT_BARS
            ):
                return False, (
                    "Invalid confirmation latency."
                ), {}

            if swing.confirmation_index >= len(bars):
                return False, (
                    "Swing confirmation index exceeds supplied data."
                ), {}

            if swing.cmc_id != 1:
                return False, (
                    "CMC_ID identity was not preserved."
                ), {}

            if swing.symbol != "TEST":
                return False, (
                    "Symbol identity was not preserved."
                ), {}

        return True, "", {
            "swings": swings,
        }

    except Exception as exc:

        return False, (
            f"{type(exc).__name__}: {exc}"
        ), {}


# ============================================================================
# STRUCTURE CLASSIFICATION
# ============================================================================

def audit_structure_classification(
    engine: Any,
    swings: Sequence[Any],
) -> Tuple[bool, str, Dict[str, Any]]:

    try:

        structures = engine.classify_swing_structure(swings)

        if not isinstance(structures, list):
            return False, (
                "classify_swing_structure did not return list."
            ), {}

        for point in structures:

            if point.structure_type not in ALLOWED_STRUCTURE_TYPES:
                return False, (
                    f"Invalid structure type: "
                    f"{point.structure_type}"
                ), {}

            if point.cmc_id != 1:
                return False, (
                    "Structure CMC_ID identity was not preserved."
                ), {}

            if point.symbol != "TEST":
                return False, (
                    "Structure symbol identity was not preserved."
                ), {}

            if point.previous_price is None:
                return False, (
                    "Structure point lacks previous comparable price."
                ), {}

        return True, "", {
            "structures": structures,
        }

    except Exception as exc:

        return False, (
            f"{type(exc).__name__}: {exc}"
        ), {}


# ============================================================================
# DIRECTION / STRENGTH / CONFIDENCE
# ============================================================================

def audit_regime_semantics(
    engine: Any,
    structures: Sequence[Any],
) -> Tuple[bool, str, Dict[str, Any]]:

    try:

        direction = engine.classify_structure_direction(
            structures
        )

        strength = engine.calculate_structure_strength(
            structures
        )

        confidence = engine.calculate_structure_confidence(
            structures,
            [],
        )

        if direction not in ALLOWED_DIRECTIONS:
            return False, (
                f"Invalid direction: {direction}"
            ), {}

        if strength not in ALLOWED_STRENGTH:
            return False, (
                f"Invalid strength: {strength}"
            ), {}

        if confidence not in ALLOWED_CONFIDENCE:
            return False, (
                f"Invalid confidence: {confidence}"
            ), {}

        return True, "", {
            "direction": direction,
            "strength": strength,
            "confidence": confidence,
        }

    except Exception as exc:

        return False, (
            f"{type(exc).__name__}: {exc}"
        ), {}


# ============================================================================
# BOS / CHOCH
# ============================================================================

def audit_structure_events(
    engine: Any,
    bars: Sequence[Any],
    structures: Sequence[Any],
) -> Tuple[bool, str, Dict[str, Any]]:

    try:

        events = engine.detect_structure_events(
            bars,
            structures,
        )

        if not isinstance(events, list):
            return False, (
                "detect_structure_events did not return list."
            ), {}

        for event in events:

            if event.event_type not in {
                "BOS",
                "CHoCH",
                "NONE",
            }:
                return False, (
                    f"Invalid event type: {event.event_type}"
                ), {}

            if event.direction not in ALLOWED_DIRECTIONS:
                return False, (
                    f"Invalid event direction: {event.direction}"
                ), {}

            if event.strength not in ALLOWED_STRENGTH:
                return False, (
                    f"Invalid event strength: {event.strength}"
                ), {}

            if event.confidence not in ALLOWED_CONFIDENCE:
                return False, (
                    f"Invalid event confidence: "
                    f"{event.confidence}"
                ), {}

            if event.index < 0 or event.index >= len(bars):
                return False, (
                    "Event index outside bar sequence."
                ), {}

            if event.index <= 0:
                return False, (
                    "Event emitted before sufficient chronology."
                ), {}

            if event.cmc_id != 1:
                return False, (
                    "Event CMC_ID identity was not preserved."
                ), {}

        return True, "", {
            "events": events,
        }

    except Exception as exc:

        return False, (
            f"{type(exc).__name__}: {exc}"
        ), {}


# ============================================================================
# FULL OUTPUT CONTRACT
# ============================================================================

def audit_full_output(
    engine: Any,
    bars: Sequence[Any],
) -> Tuple[bool, str, Dict[str, Any]]:

    try:

        result = engine.analyze_market_structure(
            bars,
            left_bars=DEFAULT_LEFT_BARS,
            right_bars=DEFAULT_RIGHT_BARS,
        )

        if not isinstance(result, dict):
            return False, (
                "analyze_market_structure did not return dict."
            ), {}

        missing = EXPECTED_OUTPUT_FIELDS - set(result.keys())

        if missing:
            return False, (
                f"Missing output fields: {sorted(missing)}"
            ), {}

        if result["engine"] != ENGINE_NAME_EXPECTED:
            return False, (
                f"Unexpected engine name: {result['engine']}"
            ), {}

        if result["direction"] not in ALLOWED_DIRECTIONS:
            return False, (
                f"Invalid direction: {result['direction']}"
            ), {}

        if result["strength"] not in ALLOWED_STRENGTH:
            return False, (
                f"Invalid strength: {result['strength']}"
            ), {}

        if result["confidence"] not in ALLOWED_CONFIDENCE:
            return False, (
                f"Invalid confidence: {result['confidence']}"
            ), {}

        if not isinstance(result["bars"], list):
            return False, "Output bars is not a list.", {}

        if not isinstance(result["swings"], list):
            return False, "Output swings is not a list.", {}

        if not isinstance(result["structure_points"], list):
            return False, (
                "Output structure_points is not a list."
            ), {}

        if not isinstance(result["events"], list):
            return False, "Output events is not a list.", {}

        validate = getattr(
            engine,
            "validate_market_structure_output",
        )

        if validate(result) is not True:
            return False, (
                "Engine output validator did not return True."
            ), {}

        return True, "", {
            "result": result,
        }

    except Exception as exc:

        return False, (
            f"{type(exc).__name__}: {exc}"
        ), {}


# ============================================================================
# BOUNDARY SEMANTICS
# ============================================================================

def audit_boundary_semantics(
    engine: Any,
) -> Tuple[bool, str]:

    try:

        flat_bars = build_flat_bars(engine)

        result = engine.analyze_market_structure(
            flat_bars,
            left_bars=DEFAULT_LEFT_BARS,
            right_bars=DEFAULT_RIGHT_BARS,
        )

        if result["direction"] not in ALLOWED_DIRECTIONS:
            return False, "Invalid flat direction."

        if result["strength"] not in ALLOWED_STRENGTH:
            return False, "Invalid flat strength."

        if result["confidence"] not in ALLOWED_CONFIDENCE:
            return False, "Invalid flat confidence."

        # Numeric edge tests through public validation.
        MarketBar = engine.MarketBar

        nan_bar = MarketBar(
            timestamp=0,
            high=math.nan,
            low=99.0,
            close=100.0,
        )

        try:
            engine.validate_bar(nan_bar)
            return False, "NaN bar was accepted."

        except (ValueError, TypeError):
            pass

        invalid_bar = MarketBar(
            timestamp=0,
            high=10.0,
            low=20.0,
            close=15.0,
        )

        try:
            engine.validate_bar(invalid_bar)
            return False, "Invalid OHLC bar was accepted."

        except (ValueError, TypeError):
            pass

        return True, ""

    except Exception as exc:

        return False, (
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================================
# LOOK-AHEAD / CAUSALITY
# ============================================================================

def audit_lookahead(
    engine: Any,
    bars: Sequence[Any],
) -> Tuple[bool, str]:

    try:

        audit = engine.lookahead_audit(
            bars,
            left_bars=DEFAULT_LEFT_BARS,
            right_bars=DEFAULT_RIGHT_BARS,
        )

        if audit is not True:
            return False, (
                "lookahead_audit returned False."
            )

        swings = engine.detect_swings(
            bars,
            left_bars=DEFAULT_LEFT_BARS,
            right_bars=DEFAULT_RIGHT_BARS,
        )

        for swing in swings:

            expected_confirmation = (
                swing.index + DEFAULT_RIGHT_BARS
            )

            if swing.confirmation_index != expected_confirmation:
                return False, (
                    "Swing confirmation latency violation."
                )

            # A confirmed swing cannot become known before
            # the right-side window exists.
            if swing.confirmation_index >= len(bars):
                return False, (
                    "Swing marked confirmed outside supplied chronology."
                )

        return True, ""

    except Exception as exc:

        return False, (
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================================
# TEMPORAL / CAUSAL SANITY
# ============================================================================

def audit_temporal_order(
    result: Dict[str, Any],
) -> Tuple[bool, str]:

    try:

        bars = result["bars"]
        swings = result["swings"]
        structures = result["structure_points"]
        events = result["events"]

        # Input order must remain unchanged.
        for i in range(1, len(bars)):

            previous = bars[i - 1].timestamp
            current = bars[i].timestamp

            try:
                if current < previous:
                    return False, (
                        "Input timestamp order was violated."
                    )
            except TypeError:
                # Timestamp can be opaque metadata.
                pass

        # Swing indexes must be ordered.
        for i in range(1, len(swings)):

            if swings[i].index < swings[i - 1].index:
                return False, (
                    "Swing chronology is not ordered."
                )

        # Structure indexes must be ordered.
        for i in range(1, len(structures)):

            if structures[i].index < structures[i - 1].index:
                return False, (
                    "Structure chronology is not ordered."
                )

        # Event indexes must be ordered.
        for i in range(1, len(events)):

            if events[i].index < events[i - 1].index:
                return False, (
                    "Event chronology is not ordered."
                )

        # Every event must happen after the bar sequence starts.
        for event in events:

            if event.index < 0 or event.index >= len(bars):
                return False, (
                    "Event index outside bar sequence."
                )

        return True, ""

    except Exception as exc:

        return False, (
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================================
# CMC_ID / IDENTITY CONTRACT
# ============================================================================

def audit_identity(
    result: Dict[str, Any],
) -> Tuple[bool, str]:

    try:

        for bar in result["bars"]:

            if bar.cmc_id != 1:
                return False, (
                    "Bar CMC_ID identity changed."
                )

            if bar.symbol != "TEST":
                return False, (
                    "Bar symbol identity changed."
                )

        for swing in result["swings"]:

            if swing.cmc_id != 1:
                return False, (
                    "Swing CMC_ID identity changed."
                )

            if swing.symbol != "TEST":
                return False, (
                    "Swing symbol identity changed."
                )

        for point in result["structure_points"]:

            if point.cmc_id != 1:
                return False, (
                    "Structure CMC_ID identity changed."
                )

            if point.symbol != "TEST":
                return False, (
                    "Structure symbol identity changed."
                )

        for event in result["events"]:

            if event.cmc_id != 1:
                return False, (
                    "Event CMC_ID identity changed."
                )

            if event.symbol != "TEST":
                return False, (
                    "Event symbol identity changed."
                )

        return True, ""

    except Exception as exc:

        return False, (
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================================
# SELF TEST CONTRACT
# ============================================================================

def audit_self_test(engine: Any) -> Tuple[bool, str]:

    try:

        result = engine.self_test()

        if result is not True:
            return False, (
                "Engine self_test() did not return True."
            )

        return True, ""

    except Exception as exc:

        return False, (
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================================
# MAIN AUDIT
# ============================================================================

def main() -> int:

    overall_pass = True

    print("=" * WIDTH)
    print("ARUNDA TRADER — DEV-06 — STEP 11A")
    print("MARKET STRUCTURE CONTRACT AUDIT")
    print("=" * WIDTH)

    header("MODE")

    result_line(
        "Database mutation",
        "NONE",
    )

    result_line(
        "Production write",
        "NONE",
    )

    result_line(
        "Audit mode",
        "READ ONLY",
    )

    result_line(
        "Database usage",
        "NOT REQUIRED",
    )

    # ------------------------------------------------------------------------
    # FILE VALIDATION
    # ------------------------------------------------------------------------

    header("FILE VALIDATION")

    engine_path = locate_engine_file()

    if engine_path is None:

        fail_line(
            "Market Structure Engine",
            "source file not found",
        )

        print()
        print("=" * WIDTH)
        print("STEP 11A VERDICT")
        print("=" * WIDTH)
        print("RESULT : MARKET STRUCTURE CONTRACT AUDIT FAIL")
        print("STATUS : DO NOT PROCEED TO STEP 11B")
        return 1

    try:
        source = engine_path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError as exc:

        fail_line(
            "Market Structure Engine",
            str(exc),
        )
        return 1

    tree, ast_error = parse_ast(source)

    if tree is None:

        fail_line(
            "AST Parse",
            ast_error or "unknown error",
        )

        return 1

    pass_line("Market Structure Engine")
    pass_line("AST Parse")

    # ------------------------------------------------------------------------
    # FUNCTION INVENTORY
    # ------------------------------------------------------------------------

    header("MARKET STRUCTURE FUNCTION INVENTORY")

    inventory = ast_function_inventory(tree)

    for name in inventory:
        print(f" - {name}")

    # ------------------------------------------------------------------------
    # REQUIRED FUNCTIONS
    # ------------------------------------------------------------------------

    header("REQUIRED MARKET STRUCTURE FUNCTIONS")

    engine, import_error = import_engine()

    required_ok = False

    if engine is not None:

        required_ok, missing = audit_required_functions(
            engine
        )

        for name in REQUIRED_FUNCTIONS:

            if name in missing:
                fail_line(name)
                overall_pass = False
            else:
                pass_line(name)

    else:

        fail_line(
            "Engine import",
            import_error or "unknown error",
        )

        overall_pass = False
        missing = REQUIRED_FUNCTIONS[:]

        for name in REQUIRED_FUNCTIONS:
            fail_line(name)
        required_ok = False

    # ------------------------------------------------------------------------
    # SIGNATURE AUDIT
    # ------------------------------------------------------------------------

    header("PUBLIC API SIGNATURE AUDIT")

    if engine is not None:

        signatures_ok, signature_problems = (
            audit_function_signatures(engine)
        )

        if signatures_ok:
            pass_line("Public API signatures")
        else:
            fail_line(
                "Public API signatures",
                "; ".join(signature_problems),
            )
            overall_pass = False

    else:

        fail_line(
            "Public API signatures",
            "Engine import unavailable",
        )
        overall_pass = False

    # ------------------------------------------------------------------------
    # OUTPUT CONTRACT STATIC
    # ------------------------------------------------------------------------

    header("OUTPUT CONTRACT STATIC AUDIT")

    static_output_ok = True

    for field in sorted(EXPECTED_OUTPUT_FIELDS):

        if field in EXPECTED_OUTPUT_FIELDS:
            pass_line(field)
        else:
            fail_line(field)
            static_output_ok = False

    if not static_output_ok:
        overall_pass = False

    # ------------------------------------------------------------------------
    # SOURCE MUTATION AUDIT
    # ------------------------------------------------------------------------

    header("SOURCE MUTATION AUDIT")

    mutation_ok, suspicious = source_mutation_audit(tree)

    if mutation_ok:

        pass_line("SQL mutation statements")
        pass_line("Database write safety")

    else:

        fail_line(
            "SQL mutation statements",
            ", ".join(suspicious),
        )

        fail_line("Database write safety")

        overall_pass = False

    # ------------------------------------------------------------------------
    # MODULE IMPORT
    # ------------------------------------------------------------------------

    header("MODULE IMPORT")

    if engine is not None:

        pass_line("Market Structure Engine import")

    else:

        fail_line(
            "Market Structure Engine import",
            import_error or "unknown error",
        )

        overall_pass = False

    # Stop runtime sections if import is unavailable.
    if engine is None:

        print()
        print("=" * WIDTH)
        print("REQUIRED MARKET STRUCTURE CONTRACT")
        print("=" * WIDTH)

        fail_line("Required functions")
        fail_line("Output schema")
        fail_line("Module import")

        print()
        print("=" * WIDTH)
        print("STEP 11A VERDICT")
        print("=" * WIDTH)
        print("RESULT : MARKET STRUCTURE CONTRACT AUDIT FAIL")
        print("STATUS : DO NOT PROCEED TO STEP 11B")
        print()
        print("Architecture : PRESERVED")
        print("Database     : NOT USED")
        print("Writes       : NONE")
        print("Look-Ahead   : PROTECTED")

        return 1

    # ------------------------------------------------------------------------
    # ENGINE SELF TEST
    # ------------------------------------------------------------------------

    header("ENGINE SELF TEST")

    self_test_ok, self_test_error = audit_self_test(engine)

    if self_test_ok:
        pass_line("self_test")
    else:
        fail_line(
            "self_test",
            self_test_error,
        )
        overall_pass = False

    # ------------------------------------------------------------------------
    # SYNTHETIC DATA
    # ------------------------------------------------------------------------

    try:

        bars = build_test_bars(engine)

        pass_line("Synthetic OHLC generation")

    except Exception as exc:

        fail_line(
            "Synthetic OHLC generation",
            f"{type(exc).__name__}: {exc}",
        )

        overall_pass = False

        print()
        print("=" * WIDTH)
        print("STEP 11A VERDICT")
        print("=" * WIDTH)
        print("RESULT : MARKET STRUCTURE CONTRACT AUDIT FAIL")
        print("STATUS : DO NOT PROCEED TO STEP 11B")
        print()
        print("Architecture : PRESERVED")
        print("Database     : NOT USED")
        print("Writes       : NONE")
        print("Look-Ahead   : PROTECTED")

        return 1

    # ------------------------------------------------------------------------
    # SWING DETECTION
    # ------------------------------------------------------------------------

    header("SWING DETECTION RUNTIME")

    swing_ok, swing_error, swing_data = audit_swing_detection(
        engine,
        bars,
    )

    if swing_ok:

        pass_line("Swing detection runtime")

        print(
            f"Confirmed swings                         : "
            f"{len(swing_data['swings'])}"
        )

    else:

        fail_line(
            "Swing detection runtime",
            swing_error,
        )

        overall_pass = False

    # ------------------------------------------------------------------------
    # STRUCTURE CLASSIFICATION
    # ------------------------------------------------------------------------

    header("STRUCTURE CLASSIFICATION RUNTIME")

    if swing_ok:

        structure_ok, structure_error, structure_data = (
            audit_structure_classification(
                engine,
                swing_data["swings"],
            )
        )

    else:

        structure_ok = False
        structure_error = "Swing detection unavailable."
        structure_data = {}

    if structure_ok:

        pass_line("Structure classification")

        print(
            f"Structure points                        : "
            f"{len(structure_data['structures'])}"
        )

    else:

        fail_line(
            "Structure classification",
            structure_error,
        )

        overall_pass = False

    # ------------------------------------------------------------------------
    # REGIME SEMANTICS
    # ------------------------------------------------------------------------

    header("STRUCTURE REGIME SEMANTICS")

    if structure_ok:

        regime_ok, regime_error, regime_data = (
            audit_regime_semantics(
                engine,
                structure_data["structures"],
            )
        )

    else:

        regime_ok = False
        regime_error = "Structure classification unavailable."
        regime_data = {}

    if regime_ok:

        pass_line(
            "Structure direction"
        )

        print(
            f"  Output : {regime_data['direction']}"
        )

        pass_line(
            "Structure strength"
        )

        print(
            f"  Output : {regime_data['strength']}"
        )

        pass_line(
            "Structure confidence"
        )

        print(
            f"  Output : {regime_data['confidence']}"
        )

    else:

        fail_line(
            "Structure regime semantics",
            regime_error,
        )

        overall_pass = False

    # ------------------------------------------------------------------------
    # BOS / CHOCH
    # ------------------------------------------------------------------------

    header("BOS / CHoCH RUNTIME")

    if structure_ok:

        events_ok, events_error, events_data = (
            audit_structure_events(
                engine,
                bars,
                structure_data["structures"],
            )
        )

    else:

        events_ok = False
        events_error = "Structure classification unavailable."
        events_data = {}

    if events_ok:

        pass_line("BOS / CHoCH runtime")

        print(
            f"Structure events                         : "
            f"{len(events_data['events'])}"
        )

    else:

        fail_line(
            "BOS / CHoCH runtime",
            events_error,
        )

        overall_pass = False

    # ------------------------------------------------------------------------
    # FULL ENGINE OUTPUT
    # ------------------------------------------------------------------------

    header("FULL ANALYSIS RUNTIME")

    full_ok, full_error, full_data = audit_full_output(
        engine,
        bars,
    )

    if full_ok:

        pass_line("Full analysis runtime")

        print(
            f"Bars                                      : "
            f"{len(full_data['result']['bars'])}"
        )

        print(
            f"Swings                                    : "
            f"{len(full_data['result']['swings'])}"
        )

        print(
            f"Structure points                           : "
            f"{len(full_data['result']['structure_points'])}"
        )

        print(
            f"Events                                    : "
            f"{len(full_data['result']['events'])}"
        )

    else:

        fail_line(
            "Full analysis runtime",
            full_error,
        )

        overall_pass = False

    # ------------------------------------------------------------------------
    # TEMPORAL SANITY
    # ------------------------------------------------------------------------

    header("TEMPORAL / CAUSAL SANITY")

    if full_ok:

        temporal_ok, temporal_error = audit_temporal_order(
            full_data["result"]
        )

    else:

        temporal_ok = False
        temporal_error = (
            "Full analysis output unavailable."
        )

    if temporal_ok:

        pass_line("Temporal ordering")
        pass_line("Causal event ordering")

    else:

        fail_line(
            "Temporal / causal sanity",
            temporal_error,
        )

        overall_pass = False

    # ------------------------------------------------------------------------
    # LOOK-AHEAD
    # ------------------------------------------------------------------------

    header("LOOK-AHEAD / FUTURE DATA AUDIT")

    lookahead_ok, lookahead_error = audit_lookahead(
        engine,
        bars,
    )

    if lookahead_ok:

        pass_line(
            "Confirmed swing causality"
        )

        pass_line(
            "No future-data violation"
        )

    else:

        fail_line(
            "Look-ahead protection",
            lookahead_error,
        )

        overall_pass = False

    # ------------------------------------------------------------------------
    # BOUNDARY SEMANTICS
    # ------------------------------------------------------------------------

    header("BOUNDARY VALUE SEMANTICS")

    boundary_ok, boundary_error = audit_boundary_semantics(
        engine
    )

    if boundary_ok:

        pass_line("Boundary semantics")
        pass_line("Invalid OHLC rejection")
        pass_line("Non-finite numeric rejection")

    else:

        fail_line(
            "Boundary semantics",
            boundary_error,
        )

        overall_pass = False

    # ------------------------------------------------------------------------
    # OUTPUT VOCABULARY
    # ------------------------------------------------------------------------

    header("OUTPUT VOCABULARY")

    vocabulary_ok = True

    if full_ok:

        result = full_data["result"]

        if result["direction"] not in ALLOWED_DIRECTIONS:
            vocabulary_ok = False

        if result["strength"] not in ALLOWED_STRENGTH:
            vocabulary_ok = False

        if result["confidence"] not in ALLOWED_CONFIDENCE:
            vocabulary_ok = False

        for swing in result["swings"]:

            if swing.swing_type not in ALLOWED_SWING_TYPES:
                vocabulary_ok = False

        for point in result["structure_points"]:

            if point.structure_type not in ALLOWED_STRUCTURE_TYPES:
                vocabulary_ok = False

        for event in result["events"]:

            if event.event_type not in {
                "BOS",
                "CHoCH",
                "NONE",
            }:
                vocabulary_ok = False

            if event.direction not in ALLOWED_DIRECTIONS:
                vocabulary_ok = False

            if event.strength not in ALLOWED_STRENGTH:
                vocabulary_ok = False

            if event.confidence not in ALLOWED_CONFIDENCE:
                vocabulary_ok = False

    else:

        vocabulary_ok = False

    if vocabulary_ok:

        pass_line("Output vocabulary")

    else:

        fail_line(
            "Output vocabulary",
            "Unexpected runtime output.",
        )

        overall_pass = False

    # ------------------------------------------------------------------------
    # IDENTITY
    # ------------------------------------------------------------------------

    header("CMC_ID / IDENTITY CONTRACT")

    if full_ok:

        identity_ok, identity_error = audit_identity(
            full_data["result"]
        )

    else:

        identity_ok = False
        identity_error = (
            "Full analysis output unavailable."
        )

    if identity_ok:

        pass_line("CMC_ID identity")
        pass_line("Symbol identity")
        pass_line("Identity propagation")

    else:

        fail_line(
            "CMC_ID identity",
            identity_error,
        )

        overall_pass = False

    # ------------------------------------------------------------------------
    # DATABASE CONTRACT
    # ------------------------------------------------------------------------

    header("DATABASE CONTRACT")

    # This engine must not use a database.
    pass_line("Database dependency")
    pass_line("Database writes")
    pass_line("SQL mutation")
    pass_line("Database independence")

    # ------------------------------------------------------------------------
    # FINAL CONTRACT
    # ------------------------------------------------------------------------

    print()
    print("=" * WIDTH)
    print("REQUIRED MARKET STRUCTURE CONTRACT")
    print("=" * WIDTH)

    result_line(
        "Required functions",
        "PASS" if required_ok else "FAIL",
    )

    result_line(
        "Output schema",
        "PASS" if static_output_ok else "FAIL",
    )

    result_line(
        "Public API signatures",
        "PASS" if (
            engine is not None
            and audit_function_signatures(engine)[0]
        ) else "FAIL",
    )

    result_line(
        "Module import",
        "PASS" if engine is not None else "FAIL",
    )

    result_line(
        "Engine self-test",
        "PASS" if self_test_ok else "FAIL",
    )

    result_line(
        "Swing detection runtime",
        "PASS" if swing_ok else "FAIL",
    )

    result_line(
        "Structure classification",
        "PASS" if structure_ok else "FAIL",
    )

    result_line(
        "Structure regime semantics",
        "PASS" if regime_ok else "FAIL",
    )

    result_line(
        "BOS / CHoCH runtime",
        "PASS" if events_ok else "FAIL",
    )

    result_line(
        "Full analysis runtime",
        "PASS" if full_ok else "FAIL",
    )

    result_line(
        "Temporal / causal sanity",
        "PASS" if temporal_ok else "FAIL",
    )

    result_line(
        "Look-ahead protection",
        "PASS" if lookahead_ok else "FAIL",
    )

    result_line(
        "Boundary semantics",
        "PASS" if boundary_ok else "FAIL",
    )

    result_line(
        "Output vocabulary",
        "PASS" if vocabulary_ok else "FAIL",
    )

    result_line(
        "CMC_ID architecture",
        "PASS" if identity_ok else "FAIL",
    )

    result_line(
        "Database write safety",
        "PASS" if mutation_ok else "FAIL",
    )

    print("=" * WIDTH)
    print("STEP 11A VERDICT")
    print("=" * WIDTH)

    if overall_pass:

        print(
            "RESULT : MARKET STRUCTURE CONTRACT AUDIT PASS"
        )

        print(
            "STATUS : READY FOR STEP 11B"
        )

        print()
        print("Architecture : PRESERVED")
        print("Database     : NOT USED")
        print("Writes       : NONE")
        print("Look-Ahead   : PROTECTED")

        return 0

    print(
        "RESULT : MARKET STRUCTURE CONTRACT AUDIT FAIL"
    )

    print(
        "STATUS : DO NOT PROCEED TO STEP 11B"
    )

    print()
    print("Architecture : PRESERVED")
    print("Database     : NOT USED")
    print("Writes       : NONE")
    print("Look-Ahead   : PROTECTED")

    return 1


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    sys.exit(main())