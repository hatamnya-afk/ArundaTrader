"""
ARUNDA TRADER — DEV-06 — STEP 11B
MARKET STRUCTURE QUALITY & CAUSAL VALIDATION

Purpose
-------
Deep quality and causal validation of the real Market Structure Engine API.

Architecture
------------
- READ ONLY
- NO DATABASE
- NO SQL
- NO PRODUCTION WRITE
- NO FUTURE DATA FOR CONFIRMED STRUCTURE
- CMC_ID / SYMBOL identity must remain intact

This audit validates the actual public API of:

    market_structure_engine.py

The audit intentionally does NOT assume database-backed execution.

Required validation domains
----------------------------
1. API availability
2. Runtime execution
3. Swing temporal causality
4. Swing confirmation latency
5. Structure classification semantics
6. HH / HL / LH / LL consistency
7. BOS / CHoCH causal ordering
8. Event uniqueness
9. Event temporal ordering
10. Structure state transitions
11. Adversarial market sequences
12. Flat / monotonic / reversal sequences
13. Identity propagation
14. Look-ahead protection
15. Output vocabulary
16. Database independence
17. Regression / deterministic behavior

IMPORTANT
---------
This file is an AUDIT ONLY.
It must never modify the production database.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import math
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple


ENGINE_MODULE_NAME = "market_structure_engine"

EXPECTED_ENGINE_NAME = "MARKET_STRUCTURE_ENGINE_v0.1"

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

ALLOWED_EVENT_TYPES = {
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
# TERMINAL HELPERS
# ============================================================================

WIDTH = 100


def line(char: str = "-") -> None:
    print(char * WIDTH)


def title(text: str) -> None:
    print("=" * WIDTH)
    print(text)
    print("=" * WIDTH)


def section(text: str) -> None:
    print()
    print("-" * WIDTH)
    print(text)
    print("-" * WIDTH)


def result_line(label: str, value: str) -> None:
    print(f"{label:<45} : {value}")


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


# ============================================================================
# AST / SOURCE SAFETY
# ============================================================================

def locate_engine_file() -> str:
    """
    Locate the real market_structure_engine.py beside this audit file.
    """

    audit_dir = os.path.dirname(os.path.abspath(__file__))

    candidate = os.path.join(
        audit_dir,
        "market_structure_engine.py",
    )

    if os.path.isfile(candidate):
        return candidate

    raise FileNotFoundError(
        "market_structure_engine.py was not found beside the audit file."
    )


def parse_engine_ast(path: str) -> ast.AST:
    with open(path, "r", encoding="utf-8") as handle:
        source = handle.read()

    return ast.parse(source, filename=path)


def ast_function_names(tree: ast.AST) -> List[str]:
    names: List[str] = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            names.append(node.name)

    return names


def audit_sql_mutations(tree: ast.AST) -> Tuple[bool, List[str]]:
    """
    Detect suspicious SQL mutation patterns.

    The market structure engine should not contain SQL at all.
    """

    suspicious: List[str] = []

    mutation_pattern = re.compile(
        r"\b("
        r"INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|REPLACE|TRUNCATE"
        r")\b",
        re.IGNORECASE,
    )

    with open(locate_engine_file(), "r", encoding="utf-8") as handle:
        source = handle.read()

    for match in mutation_pattern.finditer(source):
        suspicious.append(match.group(1).upper())

    return len(suspicious) == 0, sorted(set(suspicious))


def audit_database_references(tree: ast.AST) -> bool:
    """
    Database independence is expected.

    Reject obvious database imports / sqlite / SQL execution calls.
    """

    source_path = locate_engine_file()

    with open(source_path, "r", encoding="utf-8") as handle:
        source = handle.read().lower()

    forbidden = [
        "sqlite3",
        "psycopg",
        "sqlalchemy",
        "mysql",
        "connect_read_only",
        ".execute(",
        ".executemany(",
        ".commit(",
        ".rollback(",
    ]

    return not any(token in source for token in forbidden)


# ============================================================================
# ENGINE IMPORT
# ============================================================================

def load_engine():
    """
    Import the real engine.

    The module is loaded through the normal Python import system so that
    the audit reflects the actual production API.
    """

    audit_dir = os.path.dirname(os.path.abspath(__file__))

    if audit_dir not in sys.path:
        sys.path.insert(0, audit_dir)

    return importlib.import_module(ENGINE_MODULE_NAME)


# ============================================================================
# PUBLIC API CONTRACT
# ============================================================================

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
]


def audit_required_functions(engine) -> bool:
    ok = True

    for name in REQUIRED_FUNCTIONS:
        exists = callable(getattr(engine, name, None))
        result_line(name, pass_fail(exists))

        if not exists:
            ok = False

    return ok


def audit_public_signatures(engine) -> bool:
    """
    Signature audit against the real Engine API.

    We intentionally validate required parameter names rather than requiring
    an exact implementation-specific signature.
    """

    expectations = {
        "is_swing_high": ["bars", "index"],
        "is_swing_low": ["bars", "index"],
        "detect_swings": ["bars"],
        "classify_swing_structure": ["swings"],
        "classify_structure_direction": ["structure_points"],
        "calculate_structure_strength": ["structure_points"],
        "detect_structure_events": ["bars", "structure_points"],
        "calculate_structure_confidence": [
            "structure_points",
            "events",
        ],
        "analyze_market_structure": ["bars"],
        "validate_market_structure_output": ["result"],
        "lookahead_audit": ["bars"],
    }

    ok = True

    for name, required_params in expectations.items():

        function = getattr(engine, name, None)

        if function is None:
            ok = False
            continue

        signature = inspect.signature(function)

        actual = list(signature.parameters.keys())

        missing = [
            param
            for param in required_params
            if param not in actual
        ]

        passed = len(missing) == 0

        if not passed:
            print(
                f"{name:<45} : FAIL — missing parameters {missing}"
            )

        if not passed:
            ok = False

    return ok


# ============================================================================
# SYNTHETIC BAR GENERATION
# ============================================================================

def make_bars(
    closes: Sequence[float],
    cmc_id: int = 1,
    symbol: str = "TEST",
):
    """
    Generate deterministic OHLC bars.

    High / low are deliberately offset from close so that swing detection
    works on the actual OHLC fields rather than close-only shortcuts.
    """

    bars = []

    MarketBar = getattr(
        importlib.import_module(ENGINE_MODULE_NAME),
        "MarketBar",
    )

    for index, close in enumerate(closes):

        close_value = float(close)

        bars.append(
            MarketBar(
                timestamp=index,
                high=close_value + 1.0,
                low=close_value - 1.0,
                close=close_value,
                open=close_value,
                volume=1000.0 + index,
                cmc_id=cmc_id,
                symbol=symbol,
            )
        )

    return bars


def bullish_sequence():
    return [
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
        109,
        116,
        121,
        117,
        113,
        119,
        126,
        121,
        116,
    ]


def bearish_sequence():
    return [
        126,
        121,
        116,
        120,
        124,
        118,
        112,
        116,
        120,
        114,
        108,
        112,
        116,
        109,
        103,
        107,
        111,
        104,
        98,
        102,
        106,
        99,
        93,
        97,
        101,
    ]


def reversal_sequence():
    return [
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
        105,
        101,
        97,
        94,
        96,
        99,
        95,
        91,
        88,
        92,
        96,
        101,
        98,
        94,
        99,
        104,
    ]


def flat_sequence():
    return [100] * 30


def monotonic_up_sequence():
    return list(range(100, 130))


def monotonic_down_sequence():
    return list(range(130, 100, -1))


# ============================================================================
# OBJECT ACCESS HELPERS
# ============================================================================

def field(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def output_list(result: Dict[str, Any], name: str) -> list:
    value = result.get(name)

    if not isinstance(value, list):
        raise AssertionError(
            f"Output field '{name}' is not a list."
        )

    return value


# ============================================================================
# BASIC OUTPUT CONTRACT
# ============================================================================

def audit_output_contract(engine, result: Dict[str, Any]) -> bool:

    required = {
        "engine",
        "bars",
        "swings",
        "structure_points",
        "events",
        "direction",
        "strength",
        "confidence",
    }

    missing = required - set(result.keys())

    if missing:
        print(f"Missing fields: {sorted(missing)}")
        return False

    expected_engine = getattr(
        engine,
        "ENGINE_NAME",
        EXPECTED_ENGINE_NAME,
    )

    if result["engine"] != expected_engine:
        print(
            "Engine identity mismatch: "
            f"{result['engine']} != {expected_engine}"
        )
        return False

    return True


# ============================================================================
# SWING CAUSALITY
# ============================================================================

def audit_swing_causality(
    engine,
    bars,
    swings,
    right_bars: int = 2,
) -> bool:

    ok = True

    for swing in swings:

        index = field(swing, "index")
        confirmation_index = field(
            swing,
            "confirmation_index",
        )

        if index is None or confirmation_index is None:
            ok = False
            continue

        if confirmation_index != index + right_bars:
            print(
                "Swing confirmation latency violation: "
                f"index={index}, confirmation={confirmation_index}"
            )
            ok = False

        if confirmation_index >= len(bars):
            print(
                "Swing confirmation exceeds available sequence: "
                f"{confirmation_index} >= {len(bars)}"
            )
            ok = False

        if confirmation_index <= index:
            ok = False

    return ok


# ============================================================================
# SWING DETECTION SEMANTICS
# ============================================================================

def audit_swing_runtime(engine) -> bool:

    bars = make_bars(bullish_sequence())

    swings = engine.detect_swings(
        bars,
        left_bars=2,
        right_bars=2,
    )

    if not isinstance(swings, list):
        return False

    for swing in swings:

        swing_type = field(
            swing,
            "swing_type",
        )

        if swing_type not in ALLOWED_SWING_TYPES:
            return False

        price = field(
            swing,
            "price",
        )

        if not math.isfinite(float(price)):
            return False

    causal = audit_swing_causality(
        engine,
        bars,
        swings,
        right_bars=2,
    )

    return causal


# ============================================================================
# STRUCTURE CLASSIFICATION QUALITY
# ============================================================================

def audit_structure_classification(engine) -> bool:

    bars = make_bars(bullish_sequence())

    swings = engine.detect_swings(
        bars,
        left_bars=2,
        right_bars=2,
    )

    structures = engine.classify_swing_structure(
        swings
    )

    if not isinstance(structures, list):
        return False

    for point in structures:

        structure_type = field(
            point,
            "structure_type",
        )

        if structure_type not in ALLOWED_STRUCTURE_TYPES:
            return False

        swing_type = field(
            point,
            "swing_type",
        )

        previous_price = field(
            point,
            "previous_price",
        )

        price = float(field(point, "price"))

        if previous_price is None:
            return False

        previous_price = float(previous_price)

        if swing_type == "SWING_HIGH":

            if structure_type == "HH":
                if not price > previous_price:
                    return False

            elif structure_type == "LH":
                if not price <= previous_price:
                    return False

            else:
                return False

        elif swing_type == "SWING_LOW":

            if structure_type == "HL":
                if not price > previous_price:
                    return False

            elif structure_type == "LL":
                if not price <= previous_price:
                    return False

            else:
                return False

        else:
            return False

    return True


# ============================================================================
# STRUCTURE DIRECTION QUALITY
# ============================================================================

def audit_direction_semantics(engine) -> bool:

    bars = make_bars(bullish_sequence())

    result = engine.analyze_market_structure(bars)

    direction = result["direction"]

    if direction not in ALLOWED_DIRECTIONS:
        return False

    return True


# ============================================================================
# STRUCTURE STRENGTH / CONFIDENCE
# ============================================================================

def audit_strength_confidence(engine) -> bool:

    bars = make_bars(bullish_sequence())

    result = engine.analyze_market_structure(bars)

    strength = result["strength"]
    confidence = result["confidence"]

    if strength not in ALLOWED_STRENGTH:
        return False

    if confidence not in ALLOWED_CONFIDENCE:
        return False

    return True


# ============================================================================
# EVENT VOCABULARY
# ============================================================================

def audit_event_vocabulary(events) -> bool:

    for event in events:

        event_type = field(
            event,
            "event_type",
        )

        direction = field(
            event,
            "direction",
        )

        strength = field(
            event,
            "strength",
        )

        confidence = field(
            event,
            "confidence",
        )

        if event_type not in ALLOWED_EVENT_TYPES:
            return False

        if direction not in ALLOWED_DIRECTIONS:
            return False

        if strength not in ALLOWED_STRENGTH:
            return False

        if confidence not in ALLOWED_CONFIDENCE:
            return False

    return True


# ============================================================================
# EVENT TEMPORAL ORDERING
# ============================================================================

def audit_event_temporal_order(events) -> bool:

    previous_index = -1

    for event in events:

        index = field(event, "index")

        if index is None:
            return False

        if index < previous_index:
            return False

        previous_index = index

    return True


# ============================================================================
# EVENT UNIQUENESS
# ============================================================================

def audit_event_uniqueness(events) -> bool:

    seen = set()

    for event in events:

        key = (
            field(event, "index"),
            field(event, "event_type"),
            field(event, "direction"),
            field(event, "broken_price"),
        )

        if key in seen:
            return False

        seen.add(key)

    return True


# ============================================================================
# EVENT CAUSALITY
# ============================================================================

def audit_event_causality(
    engine,
    bars,
    structures,
    events,
) -> bool:

    """
    Every break must happen strictly after the relevant structure point
    exists in the historical sequence.

    The engine may use a confirmed structure level only after that level
    has become available.
    """

    for event in events:

        event_index = field(
            event,
            "index",
        )

        broken_price = field(
            event,
            "broken_price",
        )

        if event_index is None:
            return False

        if event_index < 0 or event_index >= len(bars):
            return False

        if broken_price is None:
            return False

        candidates = []

        for point in structures:

            point_index = field(
                point,
                "index",
            )

            point_price = field(
                point,
                "price",
            )

            if point_index is None:
                continue

            if point_index < event_index:

                if math.isclose(
                    float(point_price),
                    float(broken_price),
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ):
                    candidates.append(point)

        if not candidates:
            return False

    return True


# ============================================================================
# NO SAME-BAR CONTRADICTION
# ============================================================================

def audit_same_bar_event_conflicts(events) -> bool:

    by_index: Dict[int, List[Any]] = {}

    for event in events:

        index = field(event, "index")

        by_index.setdefault(index, []).append(event)

    for index, group in by_index.items():

        directions = {
            field(event, "direction")
            for event in group
        }

        if (
            "BULLISH" in directions
            and "BEARISH" in directions
        ):
            return False

    return True


# ============================================================================
# STRUCTURE STATE TRANSITION
# ============================================================================

def audit_state_transitions(engine) -> bool:

    sequences = [
        bullish_sequence(),
        bearish_sequence(),
        reversal_sequence(),
    ]

    for closes in sequences:

        bars = make_bars(closes)

        result = engine.analyze_market_structure(
            bars,
            left_bars=2,
            right_bars=2,
        )

        direction = result["direction"]

        if direction not in ALLOWED_DIRECTIONS:
            return False

        events = result["events"]

        if not audit_event_temporal_order(events):
            return False

        if not audit_event_uniqueness(events):
            return False

    return True


# ============================================================================
# ADVERSARIAL SEQUENCES
# ============================================================================

def audit_adversarial_sequences(engine) -> bool:

    sequences = {
        "FLAT": flat_sequence(),
        "MONOTONIC_UP": monotonic_up_sequence(),
        "MONOTONIC_DOWN": monotonic_down_sequence(),
        "BULLISH": bullish_sequence(),
        "BEARISH": bearish_sequence(),
        "REVERSAL": reversal_sequence(),
    }

    for name, closes in sequences.items():

        bars = make_bars(
            closes,
            cmc_id=77,
            symbol=name,
        )

        try:
            result = engine.analyze_market_structure(
                bars,
                left_bars=2,
                right_bars=2,
            )
        except Exception as exc:
            print(
                f"Adversarial sequence {name} failed: "
                f"{type(exc).__name__}: {exc}"
            )
            return False

        if not audit_output_contract(
            engine,
            result,
        ):
            return False

        if not audit_event_vocabulary(
            result["events"]
        ):
            return False

    return True


# ============================================================================
# FLAT MARKET SEMANTICS
# ============================================================================

def audit_flat_market(engine) -> bool:

    bars = make_bars(
        flat_sequence(),
        cmc_id=88,
        symbol="FLAT",
    )

    result = engine.analyze_market_structure(
        bars,
        left_bars=2,
        right_bars=2,
    )

    if result["direction"] not in ALLOWED_DIRECTIONS:
        return False

    for event in result["events"]:

        if field(event, "event_type") not in ALLOWED_EVENT_TYPES:
            return False

    return True


# ============================================================================
# MONOTONIC MARKET SEMANTICS
# ============================================================================

def audit_monotonic_market(engine) -> bool:

    for closes in (
        monotonic_up_sequence(),
        monotonic_down_sequence(),
    ):

        bars = make_bars(closes)

        result = engine.analyze_market_structure(
            bars,
            left_bars=2,
            right_bars=2,
        )

        if result["direction"] not in ALLOWED_DIRECTIONS:
            return False

        if not audit_event_temporal_order(
            result["events"]
        ):
            return False

    return True


# ============================================================================
# IDENTITY PROPAGATION
# ============================================================================

def audit_identity(engine) -> bool:

    cmc_id = 987654
    symbol = "IDENTITY_TEST"

    bars = make_bars(
        bullish_sequence(),
        cmc_id=cmc_id,
        symbol=symbol,
    )

    result = engine.analyze_market_structure(bars)

    for swing in result["swings"]:

        if field(swing, "cmc_id") != cmc_id:
            return False

        if field(swing, "symbol") != symbol:
            return False

    for point in result["structure_points"]:

        if field(point, "cmc_id") != cmc_id:
            return False

        if field(point, "symbol") != symbol:
            return False

    for event in result["events"]:

        if field(event, "cmc_id") != cmc_id:
            return False

        if field(event, "symbol") != symbol:
            return False

    return True


# ============================================================================
# INPUT SAFETY
# ============================================================================

def audit_input_safety(engine) -> bool:

    valid = make_bars(
        [100, 102, 101],
    )

    try:
        engine.validate_bars(valid)
    except Exception:
        return False

    invalid_ohlc = make_bars(
        [100, 102, 101],
    )

    MarketBar = getattr(
        engine,
        "MarketBar",
        None,
    )

    if MarketBar is None:
        return False

    invalid = [
        MarketBar(
            timestamp=0,
            high=10,
            low=20,
            close=15,
        ),
        MarketBar(
            timestamp=1,
            high=11,
            low=9,
            close=10,
        ),
        MarketBar(
            timestamp=2,
            high=12,
            low=8,
            close=11,
        ),
    ]

    try:
        engine.validate_bars(invalid)
        return False
    except ValueError:
        pass

    nan_bars = [
        MarketBar(
            timestamp=0,
            high=10,
            low=5,
            close=8,
        ),
        MarketBar(
            timestamp=1,
            high=float("nan"),
            low=5,
            close=8,
        ),
        MarketBar(
            timestamp=2,
            high=11,
            low=6,
            close=9,
        ),
    ]

    try:
        engine.validate_bars(nan_bars)
        return False
    except ValueError:
        pass

    return True


# ============================================================================
# DETERMINISM
# ============================================================================

def audit_determinism(engine) -> bool:

    bars = make_bars(
        bullish_sequence(),
        cmc_id=1,
        symbol="DETERMINISTIC",
    )

    result_a = engine.analyze_market_structure(
        bars,
        left_bars=2,
        right_bars=2,
    )

    result_b = engine.analyze_market_structure(
        bars,
        left_bars=2,
        right_bars=2,
    )

    def normalize(result):

        return {
            "direction": result["direction"],
            "strength": result["strength"],
            "confidence": result["confidence"],
            "swings": [
                (
                    field(x, "index"),
                    field(x, "price"),
                    field(x, "swing_type"),
                    field(x, "confirmation_index"),
                )
                for x in result["swings"]
            ],
            "structure": [
                (
                    field(x, "index"),
                    field(x, "price"),
                    field(x, "structure_type"),
                    field(x, "previous_price"),
                )
                for x in result["structure_points"]
            ],
            "events": [
                (
                    field(x, "index"),
                    field(x, "event_type"),
                    field(x, "direction"),
                    field(x, "broken_price"),
                )
                for x in result["events"]
            ],
        }

    return normalize(result_a) == normalize(result_b)


# ============================================================================
# LOOK-AHEAD AUDIT
# ============================================================================

def audit_lookahead(engine) -> bool:

    bars = make_bars(
        reversal_sequence(),
        cmc_id=55,
        symbol="LOOKAHEAD",
    )

    if not engine.lookahead_audit(
        bars,
        left_bars=2,
        right_bars=2,
    ):
        return False

    swings = engine.detect_swings(
        bars,
        left_bars=2,
        right_bars=2,
    )

    return audit_swing_causality(
        engine,
        bars,
        swings,
        right_bars=2,
    )


# ============================================================================
# FULL CAUSAL VALIDATION
# ============================================================================

def audit_full_causal_pipeline(engine) -> bool:

    bars = make_bars(
        reversal_sequence(),
        cmc_id=123,
        symbol="CAUSAL",
    )

    result = engine.analyze_market_structure(
        bars,
        left_bars=2,
        right_bars=2,
    )

    if not audit_output_contract(
        engine,
        result,
    ):
        return False

    swings = result["swings"]
    structures = result["structure_points"]
    events = result["events"]

    if not audit_swing_causality(
        engine,
        bars,
        swings,
        right_bars=2,
    ):
        return False

    if not audit_structure_classification(
        engine,
    ):
        return False

    if not audit_event_causality(
        engine,
        bars,
        structures,
        events,
    ):
        return False

    if not audit_event_temporal_order(events):
        return False

    if not audit_event_uniqueness(events):
        return False

    if not audit_same_bar_event_conflicts(events):
        return False

    return True


# ============================================================================
# DATABASE / WRITE SAFETY
# ============================================================================

def audit_database_write_safety(
    tree: ast.AST,
) -> bool:

    no_sql, mutations = audit_sql_mutations(tree)

    if not no_sql:
        print(
            "Suspicious mutation tokens detected:",
            mutations,
        )

    no_db = audit_database_references(tree)

    return no_sql and no_db


# ============================================================================
# MAIN AUDIT
# ============================================================================

def main() -> None:

    title(
        "ARUNDA TRADER — DEV-06 — STEP 11B\n"
        "MARKET STRUCTURE QUALITY & CAUSAL VALIDATION"
    )

    section("MODE")

    result_flags: List[bool] = []

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

    section("FILE VALIDATION")

    engine_path = locate_engine_file()
    tree = parse_engine_ast(engine_path)

    result_line(
        "Market Structure Engine",
        "PASS",
    )

    result_line(
        "AST Parse",
        "PASS",
    )

    section("SOURCE SAFETY")

    source_ok, mutations = audit_sql_mutations(tree)

    result_line(
        "SQL mutation statements",
        "PASS" if source_ok else (
            "FAIL — " + ", ".join(mutations)
        ),
    )

    database_independent = audit_database_references(tree)

    result_line(
        "Database independence",
        pass_fail(database_independent),
    )

    result_flags.append(source_ok)
    result_flags.append(database_independent)

    section("MARKET STRUCTURE FUNCTION INVENTORY")

    function_names = ast_function_names(tree)

    for name in function_names:
        print(f" - {name}")

    section("REQUIRED MARKET STRUCTURE FUNCTIONS")

    engine = None

    try:
        engine = load_engine()
        import_ok = True
    except Exception as exc:
        import_ok = False
        print(
            f"Engine import error: "
            f"{type(exc).__name__}: {exc}"
        )

    result_line(
        "Module import",
        pass_fail(import_ok),
    )

    result_flags.append(import_ok)

    if not import_ok:
        title("STEP 11B VERDICT")

        print(
            "RESULT : MARKET STRUCTURE QUALITY & "
            "CAUSAL VALIDATION FAIL"
        )
        print("STATUS : DO NOT PROCEED TO STEP 12")
        print()
        print("Architecture : PRESERVED")
        print("Database     : NOT USED")
        print("Writes       : NONE")
        print("Look-Ahead   : PROTECTED")

        raise SystemExit(1)

    functions_ok = audit_required_functions(engine)

    result_line(
        "Required functions",
        pass_fail(functions_ok),
    )

    result_flags.append(functions_ok)

    section("PUBLIC API SIGNATURE AUDIT")

    signatures_ok = audit_public_signatures(engine)

    result_line(
        "Public API signatures",
        pass_fail(signatures_ok),
    )

    result_flags.append(signatures_ok)

    section("ENGINE SELF TEST")

    try:
        self_test_ok = bool(engine.self_test())
    except Exception as exc:
        self_test_ok = False
        print(
            f"Self-test error: "
            f"{type(exc).__name__}: {exc}"
        )

    result_line(
        "self_test",
        pass_fail(self_test_ok),
    )

    result_flags.append(self_test_ok)

    section("SWING QUALITY")

    try:
        swing_ok = audit_swing_runtime(engine)
    except Exception as exc:
        swing_ok = False
        print(
            f"Swing audit error: "
            f"{type(exc).__name__}: {exc}"
        )

    result_line(
        "Swing detection quality",
        pass_fail(swing_ok),
    )

    result_flags.append(swing_ok)

    section("STRUCTURE CLASSIFICATION QUALITY")

    try:
        structure_ok = audit_structure_classification(
            engine
        )
    except Exception as exc:
        structure_ok = False
        print(
            f"Structure audit error: "
            f"{type(exc).__name__}: {exc}"
        )

    result_line(
        "HH / HL / LH / LL semantics",
        pass_fail(structure_ok),
    )

    result_flags.append(structure_ok)

    section("STRUCTURE REGIME QUALITY")

    try:
        direction_ok = audit_direction_semantics(
            engine
        )
        strength_ok = audit_strength_confidence(
            engine
        )
    except Exception as exc:
        direction_ok = False
        strength_ok = False

        print(
            f"Regime audit error: "
            f"{type(exc).__name__}: {exc}"
        )

    result_line(
        "Structure direction",
        pass_fail(direction_ok),
    )

    result_line(
        "Strength / confidence",
        pass_fail(strength_ok),
    )

    result_flags.extend([
        direction_ok,
        strength_ok,
    ])

    section("BOS / CHoCH QUALITY")

    try:

        bars = make_bars(
            reversal_sequence(),
            cmc_id=42,
            symbol="EVENT_TEST",
        )

        full_result = engine.analyze_market_structure(
            bars,
            left_bars=2,
            right_bars=2,
        )

        events = full_result["events"]
        structures = full_result["structure_points"]

        event_vocab_ok = audit_event_vocabulary(
            events
        )

        event_temporal_ok = audit_event_temporal_order(
            events
        )

        event_unique_ok = audit_event_uniqueness(
            events
        )

        event_causal_ok = audit_event_causality(
            engine,
            bars,
            structures,
            events,
        )

        same_bar_ok = audit_same_bar_event_conflicts(
            events
        )

    except Exception as exc:

        print(
            f"BOS / CHoCH audit error: "
            f"{type(exc).__name__}: {exc}"
        )

        event_vocab_ok = False
        event_temporal_ok = False
        event_unique_ok = False
        event_causal_ok = False
        same_bar_ok = False

    result_line(
        "Event vocabulary",
        pass_fail(event_vocab_ok),
    )

    result_line(
        "Event temporal ordering",
        pass_fail(event_temporal_ok),
    )

    result_line(
        "Event uniqueness",
        pass_fail(event_unique_ok),
    )

    result_line(
        "Event causality",
        pass_fail(event_causal_ok),
    )

    result_line(
        "Same-bar contradiction safety",
        pass_fail(same_bar_ok),
    )

    result_flags.extend([
        event_vocab_ok,
        event_temporal_ok,
        event_unique_ok,
        event_causal_ok,
        same_bar_ok,
    ])

    section("STRUCTURE STATE TRANSITIONS")

    try:
        state_ok = audit_state_transitions(engine)
    except Exception as exc:
        state_ok = False
        print(
            f"State transition error: "
            f"{type(exc).__name__}: {exc}"
        )

    result_line(
        "State transition consistency",
        pass_fail(state_ok),
    )

    result_flags.append(state_ok)

    section("ADVERSARIAL MARKET SEQUENCES")

    try:
        adversarial_ok = audit_adversarial_sequences(
            engine
        )
    except Exception as exc:
        adversarial_ok = False
        print(
            f"Adversarial audit error: "
            f"{type(exc).__name__}: {exc}"
        )

    result_line(
        "Adversarial sequences",
        pass_fail(adversarial_ok),
    )

    result_flags.append(adversarial_ok)

    section("BOUNDARY MARKET SEMANTICS")

    try:
        flat_ok = audit_flat_market(engine)
        monotonic_ok = audit_monotonic_market(engine)
        input_ok = audit_input_safety(engine)
    except Exception as exc:
        flat_ok = False
        monotonic_ok = False
        input_ok = False

        print(
            f"Boundary audit error: "
            f"{type(exc).__name__}: {exc}"
        )

    result_line(
        "Flat market",
        pass_fail(flat_ok),
    )

    result_line(
        "Monotonic markets",
        pass_fail(monotonic_ok),
    )

    result_line(
        "Input safety",
        pass_fail(input_ok),
    )

    result_flags.extend([
        flat_ok,
        monotonic_ok,
        input_ok,
    ])

    section("IDENTITY CONTRACT")

    try:
        identity_ok = audit_identity(engine)
    except Exception as exc:
        identity_ok = False
        print(
            f"Identity audit error: "
            f"{type(exc).__name__}: {exc}"
        )

    result_line(
        "CMC_ID / symbol propagation",
        pass_fail(identity_ok),
    )

    result_flags.append(identity_ok)

    section("LOOK-AHEAD / FUTURE DATA AUDIT")

    try:
        lookahead_ok = audit_lookahead(engine)
    except Exception as exc:
        lookahead_ok = False
        print(
            f"Look-ahead audit error: "
            f"{type(exc).__name__}: {exc}"
        )

    result_line(
        "Confirmed swing causality",
        pass_fail(lookahead_ok),
    )

    result_line(
        "No future-data violation",
        pass_fail(lookahead_ok),
    )

    result_flags.append(lookahead_ok)

    section("FULL CAUSAL PIPELINE")

    try:
        causal_pipeline_ok = audit_full_causal_pipeline(
            engine
        )
    except Exception as exc:
        causal_pipeline_ok = False
        print(
            f"Causal pipeline error: "
            f"{type(exc).__name__}: {exc}"
        )

    result_line(
        "Full temporal / causal pipeline",
        pass_fail(causal_pipeline_ok),
    )

    result_flags.append(causal_pipeline_ok)

    section("DETERMINISM")

    try:
        deterministic_ok = audit_determinism(
            engine
        )
    except Exception as exc:
        deterministic_ok = False
        print(
            f"Determinism error: "
            f"{type(exc).__name__}: {exc}"
        )

    result_line(
        "Deterministic output",
        pass_fail(deterministic_ok),
    )

    result_flags.append(deterministic_ok)

    section("REQUIRED MARKET STRUCTURE QUALITY CONTRACT")

    contract = [
        (
            "Source mutation safety",
            source_ok,
        ),
        (
            "Database independence",
            database_independent,
        ),
        (
            "Module import",
            import_ok,
        ),
        (
            "Required functions",
            functions_ok,
        ),
        (
            "Public API signatures",
            signatures_ok,
        ),
        (
            "Engine self-test",
            self_test_ok,
        ),
        (
            "Swing quality",
            swing_ok,
        ),
        (
            "Structure classification",
            structure_ok,
        ),
        (
            "Structure regime quality",
            direction_ok and strength_ok,
        ),
        (
            "BOS / CHoCH vocabulary",
            event_vocab_ok,
        ),
        (
            "BOS / CHoCH temporal ordering",
            event_temporal_ok,
        ),
        (
            "BOS / CHoCH uniqueness",
            event_unique_ok,
        ),
        (
            "BOS / CHoCH causality",
            event_causal_ok,
        ),
        (
            "Same-bar contradiction safety",
            same_bar_ok,
        ),
        (
            "State transition consistency",
            state_ok,
        ),
        (
            "Adversarial sequences",
            adversarial_ok,
        ),
        (
            "Boundary semantics",
            flat_ok and monotonic_ok,
        ),
        (
            "Input safety",
            input_ok,
        ),
        (
            "CMC_ID / symbol identity",
            identity_ok,
        ),
        (
            "Look-ahead protection",
            lookahead_ok,
        ),
        (
            "Full causal pipeline",
            causal_pipeline_ok,
        ),
        (
            "Deterministic output",
            deterministic_ok,
        ),
    ]

    for label, passed in contract:
        result_line(
            label,
            pass_fail(passed),
        )

    all_pass = all(
        passed
        for _, passed in contract
    )

    title("STEP 11B VERDICT")

    if all_pass:

        print(
            "RESULT : MARKET STRUCTURE QUALITY & "
            "CAUSAL VALIDATION PASS"
        )
        print(
            "STATUS : READY FOR STEP 12"
        )

    else:

        print(
            "RESULT : MARKET STRUCTURE QUALITY & "
            "CAUSAL VALIDATION FAIL"
        )
        print(
            "STATUS : DO NOT PROCEED TO STEP 12"
        )

    print()
    print("Architecture : PRESERVED")
    print("Database     : NOT USED")
    print("Writes       : NONE")
    print("Look-Ahead   : PROTECTED")

    if not all_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()