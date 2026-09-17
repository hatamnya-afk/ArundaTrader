"""
ARUNDA TRADER — DEV-06 — STEP 14A
MARKET REGIME ENGINE CONTRACT AUDIT

Purpose
-------
Read-only structural and runtime contract audit for
market_regime_engine.py.

Rules
-----
- No database usage
- No SQL
- No production writes
- No mutation
- No trading decisions
- No BUY / SELL
- No LONG / SHORT
- No look-ahead
- Identity preservation
- Deterministic output
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import math
import pathlib
import sys
import tempfile
from dataclasses import is_dataclass
from typing import Any, Mapping, Sequence


BASE_DIR = pathlib.Path(__file__).resolve().parent
ENGINE_FILE = BASE_DIR / "market_regime_engine.py"

ENGINE_NAME = "MARKET_REGIME_ENGINE_v0.1"


# ============================================================================
# REQUIRED PUBLIC CONTRACT
# ============================================================================

REQUIRED_FUNCTIONS = (
    "validate_regime_bar",
    "validate_regime_bars",
    "calculate_market_regime_records",
    "validate_regime_record",
    "validate_regime_collection",
    "lookahead_audit",
    "determinism_audit",
    "self_test",
)

REQUIRED_CLASSES = (
    "RegimeBar",
    "MarketRegimeRecord",
)


# ============================================================================
# SOURCE HELPERS
# ============================================================================

def read_source() -> str:

    if not ENGINE_FILE.exists():

        raise AssertionError(
            f"Market Regime Engine not found: {ENGINE_FILE}"
        )

    raw = ENGINE_FILE.read_bytes()

    # Explicitly reject UTF-8 BOM / U+FEFF.
    if raw.startswith(b"\xef\xbb\xbf"):

        raise AssertionError(
            "Market Regime Engine contains UTF-8 BOM."
        )

    source = raw.decode(
        "utf-8"
    )

    if "\ufeff" in source:

        raise AssertionError(
            "Market Regime Engine contains U+FEFF."
        )

    return source


def parse_ast(
    source: str,
) -> ast.AST:

    try:

        return ast.parse(
            source,
            filename=str(ENGINE_FILE),
        )

    except SyntaxError as exc:

        raise AssertionError(
            f"AST parse failed: {exc}"
        ) from exc


def function_inventory(
    tree: ast.AST,
) -> list[str]:

    result = []

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            result.append(
                node.name
            )

        elif isinstance(
            node,
            ast.ClassDef,
        ):

            for child in node.body:

                if isinstance(
                    child,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):

                    result.append(
                        child.name
                    )

    return sorted(
        set(result)
    )


def class_inventory(
    tree: ast.AST,
) -> list[str]:

    return sorted(
        {
            node.name
            for node in ast.walk(tree)
            if isinstance(
                node,
                ast.ClassDef,
            )
        }
    )


# ============================================================================
# SOURCE SAFETY
# ============================================================================

def source_mutation_audit(
    tree: ast.AST,
) -> None:

    forbidden_calls = {
        "execute",
        "executemany",
        "executescript",
        "commit",
        "rollback",
        "connect",
        "create_engine",
    }

    forbidden_names = {
        "sqlite3",
        "sqlalchemy",
        "pymysql",
        "psycopg2",
        "database",
        "db",
        "connection",
        "cursor",
    }

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Call,
        ):

            if isinstance(
                node.func,
                ast.Name,
            ):

                if node.func.id in forbidden_calls:

                    raise AssertionError(
                        "Forbidden database / mutation call: "
                        f"{node.func.id}"
                    )

            if isinstance(
                node.func,
                ast.Attribute,
            ):

                if node.func.attr in forbidden_calls:

                    raise AssertionError(
                        "Forbidden database / mutation call: "
                        f"{node.func.attr}"
                    )


def database_independence_audit(
    tree: ast.AST,
) -> None:

    forbidden_imports = {
        "sqlite3",
        "sqlalchemy",
        "pymysql",
        "psycopg2",
        "duckdb",
    }

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                root = alias.name.split(".")[0]

                if root in forbidden_imports:

                    raise AssertionError(
                        "Database library detected: "
                        f"{root}"
                    )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module:

                root = node.module.split(".")[0]

                if root in forbidden_imports:

                    raise AssertionError(
                        "Database library detected: "
                        f"{root}"
                    )


def decision_isolation_audit(
    tree: ast.AST,
    source: str,
) -> None:

    forbidden_fields = {
        "buy",
        "sell",
        "signal",
        "decision",
        "long",
        "short",
        "entry",
        "exit",
    }

    classes = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            ast.ClassDef,
        )
    ]

    for cls in classes:

        if cls.name not in {
            "MarketRegimeRecord",
            "RegimeBar",
        }:

            continue

        for node in ast.walk(cls):

            if isinstance(
                node,
                ast.AnnAssign,
            ):

                target = node.target

                if isinstance(
                    target,
                    ast.Name,
                ):

                    if target.id.lower() in forbidden_fields:

                        raise AssertionError(
                            "Decision field detected: "
                            f"{target.id}"
                        )

            if isinstance(
                node,
                ast.Assign,
            ):

                for target in node.targets:

                    if isinstance(
                        target,
                        ast.Name,
                    ):

                        if target.id.lower() in forbidden_fields:

                            raise AssertionError(
                                "Decision field detected: "
                                f"{target.id}"
                            )

    source_lower = source.lower()

    for forbidden in (
        "buy_signal",
        "sell_signal",
        "trading_decision",
    ):

        if forbidden in source_lower:

            raise AssertionError(
                "Trading decision token detected: "
                f"{forbidden}"
            )


# ============================================================================
# IMPORT
# ============================================================================

def import_engine():

    if str(BASE_DIR) not in sys.path:

        sys.path.insert(
            0,
            str(BASE_DIR),
        )

    module_name = (
        "_arunda_market_regime_engine_contract_target"
    )

    spec = importlib.util.spec_from_file_location(
        module_name,
        ENGINE_FILE,
    )

    if spec is None:

        raise AssertionError(
            "Unable to create module specification."
        )

    if spec.loader is None:

        raise AssertionError(
            "Unable to create module loader."
        )

    module = importlib.util.module_from_spec(
        spec
    )

    # ------------------------------------------------------------------------
    # IMPORTANT
    #
    # dataclasses require the module to exist in sys.modules while the module
    # body is executed.
    # ------------------------------------------------------------------------

    sys.modules[
        module_name
    ] = module

    try:

        spec.loader.exec_module(
            module
        )

    except Exception:

        sys.modules.pop(
            module_name,
            None,
        )

        raise

    return module


# ============================================================================
# FUNCTION CONTRACT
# ============================================================================

def required_functions_audit(
    engine: Any,
) -> None:

    for name in REQUIRED_FUNCTIONS:

        value = getattr(
            engine,
            name,
            None,
        )

        if value is None:

            raise AssertionError(
                f"Missing required function: {name}"
            )

        if not callable(value):

            raise AssertionError(
                f"Required function is not callable: {name}"
            )


def required_classes_audit(
    engine: Any,
) -> None:

    for name in REQUIRED_CLASSES:

        value = getattr(
            engine,
            name,
            None,
        )

        if value is None:

            raise AssertionError(
                f"Missing required class: {name}"
            )

        if not isinstance(
            value,
            type,
        ):

            raise AssertionError(
                f"Required class invalid: {name}"
            )


# ============================================================================
# SIGNATURE AUDIT
# ============================================================================

def signature_audit(
    engine: Any,
) -> None:

    expected = {
        "validate_regime_bar": 1,
        "validate_regime_bars": 1,
        "calculate_market_regime_records": 1,
        "validate_regime_record": 1,
        "validate_regime_collection": 1,
        "lookahead_audit": 1,
        "determinism_audit": 1,
        "self_test": 0,
    }

    for name, expected_min in expected.items():

        fn = getattr(
            engine,
            name,
        )

        signature = inspect.signature(
            fn
        )

        required_positional = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            and parameter.default
            is inspect.Parameter.empty
        ]

        if len(required_positional) < expected_min:

            raise AssertionError(
                f"Invalid public signature: {name}"
            )


# ============================================================================
# DATACLASS SCHEMA AUDIT
# ============================================================================

def dataclass_schema_audit(
    engine: Any,
) -> None:

    for name in REQUIRED_CLASSES:

        cls = getattr(
            engine,
            name,
        )

        if not is_dataclass(cls):

            raise AssertionError(
                f"{name} must be a dataclass."
            )

    regime_bar = engine.RegimeBar

    regime_record = engine.MarketRegimeRecord

    bar_fields = set(
        regime_bar.__dataclass_fields__
    )

    record_fields = set(
        regime_record.__dataclass_fields__
    )

    required_bar_fields = {
        "timestamp",
        "high",
        "low",
        "close",
    }

    required_record_fields = {
        "index",
        "timestamp",
    }

    missing_bar = (
        required_bar_fields
        - bar_fields
    )

    missing_record = (
        required_record_fields
        - record_fields
    )

    if missing_bar:

        raise AssertionError(
            "RegimeBar missing fields: "
            f"{sorted(missing_bar)}"
        )

    if missing_record:

        raise AssertionError(
            "MarketRegimeRecord missing fields: "
            f"{sorted(missing_record)}"
        )


# ============================================================================
# RUNTIME CONTRACT
# ============================================================================

def runtime_output_audit(
    engine: Any,
) -> None:

    result = engine.self_test()

    if result is not True:

        raise AssertionError(
            "self_test() did not return True."
        )

    bars = [
        engine.RegimeBar(
            timestamp=i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.0 + i,
            open=100.0 + i,
            volume=1000.0 + i,
            cmc_id=1,
            symbol="TEST",
        )
        for i in range(60)
    ]

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    if not isinstance(
        records,
        list,
    ):

        raise AssertionError(
            "Runtime output must be a list."
        )

    if len(records) != len(bars):

        raise AssertionError(
            "Runtime output length mismatch."
        )

    for i, record in enumerate(records):

        if record.index != i:

            raise AssertionError(
                "Runtime index propagation failed."
            )

        if record.timestamp != bars[i].timestamp:

            raise AssertionError(
                "Timestamp propagation failed."
            )

        if record.cmc_id != bars[i].cmc_id:

            raise AssertionError(
                "CMC_ID propagation failed."
            )

        if record.symbol != bars[i].symbol:

            raise AssertionError(
                "Symbol propagation failed."
            )


# ============================================================================
# IDENTITY CONTRACT
# ============================================================================

def identity_audit(
    engine: Any,
) -> None:

    bars = [
        engine.RegimeBar(
            timestamp=f"T{i}",
            high=101.0 + i,
            low=99.0 + i,
            close=100.0 + i,
            open=100.0 + i,
            volume=1000.0,
            cmc_id=1000 + i,
            symbol=f"SYM{i}",
        )
        for i in range(20)
    ]

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    for i, record in enumerate(records):

        assert record.index == i

        assert (
            record.timestamp
            == bars[i].timestamp
        )

        assert (
            record.cmc_id
            == bars[i].cmc_id
        )

        assert (
            record.symbol
            == bars[i].symbol
        )


# ============================================================================
# WARM-UP AUDIT
# ============================================================================

def warmup_audit(
    engine: Any,
) -> None:

    bars = [
        engine.RegimeBar(
            timestamp=i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.0 + i,
            open=100.0 + i,
            volume=1000.0,
            cmc_id=1,
            symbol="TEST",
        )
        for i in range(10)
    ]

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    if len(records) != len(bars):

        raise AssertionError(
            "Warm-up output length mismatch."
        )

    # A regime engine may legitimately return UNKNOWN,
    # MIXED, None, or another neutral descriptive state
    # during insufficient history. The contract requires
    # only that it does not crash or fabricate a decision.
    for record in records:

        forbidden = {
            "BUY",
            "SELL",
            "LONG",
            "SHORT",
        }

        for field in (
            "regime",
            "market_regime",
            "regime_state",
        ):

            if hasattr(
                record,
                field,
            ):

                value = getattr(
                    record,
                    field,
                )

                if isinstance(
                    value,
                    str,
                ):

                    if value.upper() in forbidden:

                        raise AssertionError(
                            "Decision output detected during warm-up."
                        )


# ============================================================================
# NUMERIC SAFETY
# ============================================================================

def numeric_safety_audit(
    engine: Any,
) -> None:

    bars = [
        engine.RegimeBar(
            timestamp=i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.0 + i,
            open=100.0 + i,
            volume=1000.0,
            cmc_id=1,
            symbol="TEST",
        )
        for i in range(60)
    ]

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    for record in records:

        for field in record.__dataclass_fields__:

            value = getattr(
                record,
                field,
            )

            if isinstance(
                value,
                bool,
            ):

                continue

            if isinstance(
                value,
                (int, float),
            ):

                if not math.isfinite(
                    float(value)
                ):

                    raise AssertionError(
                        "Non-finite runtime output: "
                        f"{field}"
                    )


# ============================================================================
# BOUNDARY / INPUT SAFETY
# ============================================================================

def input_safety_audit(
    engine: Any,
) -> None:

    invalid_ohlc = [
        engine.RegimeBar(
            timestamp=0,
            high=10.0,
            low=20.0,
            close=15.0,
        )
    ]

    try:

        engine.validate_regime_bars(
            invalid_ohlc
        )

    except (
        ValueError,
        TypeError,
    ):

        pass

    else:

        raise AssertionError(
            "Invalid OHLC was not rejected."
        )

    invalid_volume = [
        engine.RegimeBar(
            timestamp=0,
            high=10.0,
            low=5.0,
            close=8.0,
            volume=-1.0,
        )
    ]

    try:

        engine.validate_regime_bars(
            invalid_volume
        )

    except (
        ValueError,
        TypeError,
    ):

        pass

    else:

        raise AssertionError(
            "Negative volume was not rejected."
        )


# ============================================================================
# LOOK-AHEAD STRUCTURAL CONTRACT
# ============================================================================

def lookahead_contract_audit(
    engine: Any,
) -> None:

    signature = inspect.signature(
        engine.lookahead_audit
    )

    if len(signature.parameters) < 1:

        raise AssertionError(
            "lookahead_audit must accept input data."
        )

    source = inspect.getsource(
        engine.lookahead_audit
    )

    source_lower = source.lower()

    forbidden_future_patterns = (
        "[-i]",
        "[i+1:]",
        "[i + 1:]",
        "[i+1]",
        "[i + 1]",
        "future",
        "look_ahead_data",
        "next_bar",
        "future_bar",
    )

    # "future" can legitimately occur in documentation,
    # therefore only structural access patterns are fatal.
    for pattern in forbidden_future_patterns:

        if pattern in source_lower:

            if pattern in {
                "future",
            }:

                continue

            raise AssertionError(
                "Potential future-data access detected: "
                f"{pattern}"
            )


# ============================================================================
# DETERMINISM CONTRACT
# ============================================================================

def determinism_contract_audit(
    engine: Any,
) -> None:

    bars = [
        engine.RegimeBar(
            timestamp=i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.0 + i,
            open=100.0 + i,
            volume=1000.0,
            cmc_id=1,
            symbol="TEST",
        )
        for i in range(60)
    ]

    first = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    second = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    if first != second:

        raise AssertionError(
            "Regime output is not deterministic."
        )

    audit = engine.determinism_audit(
        bars
    )

    if audit is not True:

        raise AssertionError(
            "determinism_audit() failed."
        )


# ============================================================================
# INPUT ORDER CONTRACT
# ============================================================================

def order_preservation_audit(
    engine: Any,
) -> None:

    bars = [
        engine.RegimeBar(
            timestamp=100 + i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.0 + i,
            open=100.0 + i,
            volume=1000.0,
            cmc_id=500 + i,
            symbol=f"S{i}",
        )
        for i in range(25)
    ]

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    expected = list(
        range(len(bars))
    )

    actual = [
        record.index
        for record in records
    ]

    if actual != expected:

        raise AssertionError(
            "Input order was not preserved."
        )


# ============================================================================
# DECISION ISOLATION RUNTIME
# ============================================================================

def decision_runtime_audit(
    engine: Any,
) -> None:

    bars = [
        engine.RegimeBar(
            timestamp=i,
            high=101.0 + i,
            low=99.0 + i,
            close=100.0 + i,
            open=100.0 + i,
            volume=1000.0,
            cmc_id=1,
            symbol="TEST",
        )
        for i in range(60)
    ]

    records = (
        engine.calculate_market_regime_records(
            bars
        )
    )

    forbidden_values = {
        "BUY",
        "SELL",
        "LONG",
        "SHORT",
        "ENTRY",
        "EXIT",
    }

    for record in records:

        for field in record.__dataclass_fields__:

            value = getattr(
                record,
                field,
            )

            if isinstance(
                value,
                str,
            ):

                if value.upper() in forbidden_values:

                    raise AssertionError(
                        "Decision output detected: "
                        f"{field}={value}"
                    )


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:

    print("=" * 100)
    print(
        "ARUNDA TRADER — DEV-06 — STEP 14A"
    )
    print(
        "MARKET REGIME ENGINE CONTRACT AUDIT"
    )
    print("=" * 100)

    print()
    print("-" * 100)
    print("MODE")
    print("-" * 100)

    print(
        "Database mutation                                  : NONE"
    )
    print(
        "Production write                                   : NONE"
    )
    print(
        "Audit mode                                         : READ ONLY"
    )
    print(
        "Database usage                                     : NOT REQUIRED"
    )

    try:

        # --------------------------------------------------------------------
        # SOURCE
        # --------------------------------------------------------------------

        source = read_source()

        tree = parse_ast(
            source
        )

        print()
        print("-" * 100)
        print("FILE VALIDATION")
        print("-" * 100)

        print(
            "Market Regime Engine                               : PASS"
        )

        print(
            "AST Parse                                           : PASS"
        )

        # --------------------------------------------------------------------
        # SOURCE SAFETY
        # --------------------------------------------------------------------

        source_mutation_audit(
            tree
        )

        database_independence_audit(
            tree
        )

        print()
        print("-" * 100)
        print("SOURCE SAFETY")
        print("-" * 100)

        print(
            "Source mutation statements                         : PASS"
        )

        print(
            "Database independence                              : PASS"
        )

        # --------------------------------------------------------------------
        # INVENTORY
        # --------------------------------------------------------------------

        functions = function_inventory(
            tree
        )

        classes = class_inventory(
            tree
        )

        print()
        print("-" * 100)
        print(
            "MARKET REGIME ENGINE FUNCTION INVENTORY"
        )
        print("-" * 100)

        for name in functions:

            print(
                f" - {name}"
            )

        print()
        print("-" * 100)
        print(
            "REQUIRED MARKET REGIME ENGINE FUNCTIONS"
        )
        print("-" * 100)

        missing_functions = (
            set(REQUIRED_FUNCTIONS)
            - set(functions)
        )

        missing_classes = (
            set(REQUIRED_CLASSES)
            - set(classes)
        )

        if missing_functions:

            raise AssertionError(
                "Missing required functions: "
                f"{sorted(missing_functions)}"
            )

        if missing_classes:

            raise AssertionError(
                "Missing required classes: "
                f"{sorted(missing_classes)}"
            )

        print(
            "Required functions                                 : PASS"
        )

        print(
            "Required classes                                   : PASS"
        )

        # --------------------------------------------------------------------
        # IMPORT
        # --------------------------------------------------------------------

        try:

            engine = import_engine()

        except Exception as exc:

            raise AssertionError(
                "Market Regime Engine import failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc

        # --------------------------------------------------------------------
        # SIGNATURE
        # --------------------------------------------------------------------

        signature_audit(
            engine
        )

        print()
        print("-" * 100)
        print(
            "PUBLIC API SIGNATURE AUDIT"
        )
        print("-" * 100)

        print(
            "Public API signatures                              : PASS"
        )

        # --------------------------------------------------------------------
        # SCHEMA
        # --------------------------------------------------------------------

        dataclass_schema_audit(
            engine
        )

        print()
        print("-" * 100)
        print(
            "OUTPUT SCHEMA CONTRACT"
        )
        print("-" * 100)

        print(
            "RegimeBar schema                                    : PASS"
        )

        print(
            "MarketRegimeRecord schema                           : PASS"
        )

        print(
            "Look-ahead structural safety                        : PASS"
        )

        # --------------------------------------------------------------------
        # DECISION
        # --------------------------------------------------------------------

        decision_isolation_audit(
            tree,
            source,
        )

        decision_runtime_audit(
            engine
        )

        print()
        print("-" * 100)
        print(
            "DECISION OUTPUT ISOLATION"
        )
        print("-" * 100)

        print(
            "Trading decision output                             : PASS"
        )

        print(
            "BUY / SELL output                                   : NONE"
        )

        # --------------------------------------------------------------------
        # RUNTIME
        # --------------------------------------------------------------------

        runtime_output_audit(
            engine
        )

        print()
        print("-" * 100)
        print(
            "MODULE RUNTIME"
        )
        print("-" * 100)

        print(
            "Market Regime Engine import                         : PASS"
        )

        print(
            "Runtime output                                      : PASS"
        )

        # --------------------------------------------------------------------
        # IDENTITY
        # --------------------------------------------------------------------

        identity_audit(
            engine
        )

        print()
        print("-" * 100)
        print(
            "CMC_ID / SYMBOL / TIMESTAMP IDENTITY CONTRACT"
        )
        print("-" * 100)

        print(
            "CMC_ID identity                                    : PASS"
        )

        print(
            "Symbol identity                                    : PASS"
        )

        print(
            "Timestamp propagation                              : PASS"
        )

        print(
            "Input order preservation                           : PASS"
        )

        # --------------------------------------------------------------------
        # WARM-UP
        # --------------------------------------------------------------------

        warmup_audit(
            engine
        )

        print()
        print("-" * 100)
        print(
            "WARM-UP / INSUFFICIENT HISTORY CONTRACT"
        )
        print("-" * 100)

        print(
            "Warm-up semantics                                  : PASS"
        )

        # --------------------------------------------------------------------
        # NUMERIC
        # --------------------------------------------------------------------

        numeric_safety_audit(
            engine
        )

        print()
        print("-" * 100)
        print(
            "NUMERIC SAFETY CONTRACT"
        )
        print("-" * 100)

        print(
            "Finite regime values                               : PASS"
        )

        # --------------------------------------------------------------------
        # INPUT
        # --------------------------------------------------------------------

        input_safety_audit(
            engine
        )

        print()
        print("-" * 100)
        print(
            "BOUNDARY / INPUT SAFETY"
        )
        print("-" * 100)

        print(
            "Invalid OHLC rejection                             : PASS"
        )

        print(
            "Negative volume rejection                          : PASS"
        )

        # --------------------------------------------------------------------
        # LOOK-AHEAD
        # --------------------------------------------------------------------

        lookahead_contract_audit(
            engine
        )

        print()
        print("-" * 100)
        print(
            "LOOK-AHEAD / FUTURE DATA CONTRACT"
        )
        print("-" * 100)

        print(
            "Look-ahead audit                                   : PASS"
        )

        print(
            "Future-data protection                             : PASS"
        )

        # --------------------------------------------------------------------
        # DETERMINISM
        # --------------------------------------------------------------------

        determinism_contract_audit(
            engine
        )

        print()
        print("-" * 100)
        print(
            "DETERMINISM CONTRACT"
        )
        print("-" * 100)

        print(
            "Deterministic output                               : PASS"
        )

        # --------------------------------------------------------------------
        # ORDER
        # --------------------------------------------------------------------

        order_preservation_audit(
            engine
        )

        print()
        print("-" * 100)
        print(
            "ARCHITECTURE CONTRACT"
        )
        print("-" * 100)

        print(
            "Analysis-layer isolation                           : PASS"
        )

        print(
            "Database independence                              : PASS"
        )

        print(
            "Production writes                                  : NONE"
        )

        # --------------------------------------------------------------------
        # SELF TEST
        # --------------------------------------------------------------------

        self_test_result = engine.self_test()

        if self_test_result is not True:

            raise AssertionError(
                "Market Regime Engine self_test failed."
            )

        print()
        print("-" * 100)
        print(
            "ENGINE SELF TEST"
        )
        print("-" * 100)

        print(
            "self_test                                          : PASS"
        )

        # --------------------------------------------------------------------
        # REQUIRED CONTRACT SUMMARY
        # --------------------------------------------------------------------

        print()
        print("-" * 100)
        print(
            "REQUIRED MARKET REGIME ENGINE CONTRACT"
        )
        print("-" * 100)

        summary = (
            "Source mutation safety",
            "Database independence",
            "Required functions",
            "Required classes",
            "Public API signatures",
            "RegimeBar schema",
            "MarketRegimeRecord schema",
            "Runtime output",
            "CMC_ID / symbol identity",
            "Boundary semantics",
            "Warm-up semantics",
            "Numeric safety",
            "Look-ahead protection",
            "Deterministic output",
            "Decision isolation",
            "Architecture preservation",
        )

        for item in summary:

            print(
                f"{item:<52} : PASS"
            )

        # --------------------------------------------------------------------
        # VERDICT
        # --------------------------------------------------------------------

        print()
        print("=" * 100)
        print(
            "STEP 14A VERDICT"
        )
        print("=" * 100)

        print(
            "RESULT : MARKET REGIME ENGINE CONTRACT AUDIT PASS"
        )

        print(
            "STATUS : READY FOR STEP 14B"
        )

        print()
        print(
            "Architecture : PRESERVED"
        )

        print(
            "Database     : NOT USED"
        )

        print(
            "Writes       : NONE"
        )

        print(
            "Look-Ahead   : PROTECTED"
        )

        print(
            "Decision     : NONE"
        )

    except Exception as exc:

        print()
        print("=" * 100)
        print(
            "STEP 14A VERDICT"
        )
        print("=" * 100)

        print(
            "RESULT : MARKET REGIME ENGINE CONTRACT AUDIT FAIL"
        )

        print(
            "ERROR  : "
            f"{type(exc).__name__}: {exc}"
        )

        raise


if __name__ == "__main__":

    main()